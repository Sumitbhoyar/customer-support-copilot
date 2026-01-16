"""
Step Functions orchestration for the agentic workflow.

Tasks:
- Classify ticket
- Retrieve context
- Generate drafts with guardrail fallback
- Return structured output
"""

from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class OrchestrationConstruct(Construct):
    """Provision lambdas per stage and a low-cost state machine."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        lambda_code: _lambda.Code,
        shared_env: dict,
        vpc: ec2.IVpc | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        # Stage Lambdas reuse the same source code to keep packaging simple.
        common_lambda_kwargs = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=lambda_code,
            memory_size=512,
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.ARM_64,
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment=shared_env,
        )
        if vpc:
            common_lambda_kwargs["vpc"] = vpc

        classify_fn = _lambda.Function(
            self, "ClassifyHandler", handler="handlers.classification.lambda_handler", **common_lambda_kwargs
        )
        retrieve_fn = _lambda.Function(
            self, "RetrieveHandler", handler="handlers.retrieval.lambda_handler", **common_lambda_kwargs
        )
        respond_fn = _lambda.Function(
            self, "RespondHandler", handler="handlers.response_generation.lambda_handler", **common_lambda_kwargs
        )
        self.classify_fn = classify_fn
        self.retrieve_fn = retrieve_fn
        self.respond_fn = respond_fn

        # Step Functions definition.
        classify_task = tasks.LambdaInvoke(
            self,
            "Classify",
            lambda_function=classify_fn,
            payload=sfn.TaskInput.from_object({"ticket.$": "$.ticket"}),
            payload_response_only=True,
            retry_on_service_exceptions=True,
            result_path="$.classification",
        )

        retrieve_task = tasks.LambdaInvoke(
            self,
            "Retrieve",
            lambda_function=retrieve_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "ticket.$": "$.ticket",
                    "classification.$": "$.classification",
                }
            ),
            payload_response_only=True,
            result_path="$.context",
        )

        generate_task = tasks.LambdaInvoke(
            self,
            "Generate",
            lambda_function=respond_fn,
            payload=sfn.TaskInput.from_object(
                {
                    "ticket.$": "$.ticket",
                    "classification.$": "$.classification",
                    "context.$": "$.context",
                }
            ),
            payload_response_only=True,
            result_path="$.generation",
        )

        definition = (
            classify_task
            .next(retrieve_task)
            .next(generate_task)
            .next(
                sfn.Pass(
                    self,
                    "AssembleOutput",
                    parameters={
                        "classification": sfn.JsonPath.string_at("$.classification"),
                        "context": sfn.JsonPath.string_at("$.context"),
                        "generation": sfn.JsonPath.string_at("$.generation"),
                        "next_actions": ["Send draft to agent queue for review"],
                        "trace": {
                            "classification_latency_ms": 0,
                            "retrieval_latency_ms": 0,
                            "generation_latency_ms": 0,
                            "total_latency_ms": 0,
                            "state": "completed",
                            "started_at.$": "$$.Execution.StartTime",
                            "correlation_id.$": "$.correlation_id",
                        },
                    },
                )
            )
        )

        self.state_machine = sfn.StateMachine(
            self,
            "AgenticWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            state_machine_name=f"ai-support-agent-{environment}",
            timeout=Duration.minutes(5),
            tracing_enabled=True,
            state_machine_type=sfn.StateMachineType.EXPRESS,
        )
