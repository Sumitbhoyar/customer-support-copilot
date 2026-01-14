"""
CDK app entrypoint.

Creates the AI Support stack with cost-optimized defaults.
"""

import aws_cdk as cdk

from infrastructure.config.settings import Settings
from infrastructure.main_stack import AISupportStack


def main() -> None:
    """Instantiate the CDK app and stack."""
    settings = Settings.from_environment()
    app = cdk.App()

    AISupportStack(
        app,
        f"AISupportStack-{settings.environment}",
        settings=settings,
        env=cdk.Environment(
            account=app.node.try_get_context("account"),
            region=settings.aws_region,
        ),
    )

    app.synth()


if __name__ == "__main__":
    main()
