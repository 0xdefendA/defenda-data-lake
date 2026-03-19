from utils.dotdict import DotDict
import logging

logger = logging.getLogger()

# Map AWS event sources to human-readable categories
CATEGORY_MAP = {
    "signin.amazonaws.com": "authentication",
    "sts.amazonaws.com": "authentication",
    "sso.amazonaws.com": "authentication",
    "iam.amazonaws.com": "iam",
    "organizations.amazonaws.com": "iam",
    "s3.amazonaws.com": "storage",
    "ec2.amazonaws.com": "compute",
    "lambda.amazonaws.com": "compute",
    "ecs.amazonaws.com": "compute",
    "eks.amazonaws.com": "compute",
    "rds.amazonaws.com": "database",
    "dynamodb.amazonaws.com": "database",
    "kms.amazonaws.com": "encryption",
    "secretsmanager.amazonaws.com": "secrets",
    "cloudtrail.amazonaws.com": "audit",
    "config.amazonaws.com": "audit",
    "guardduty.amazonaws.com": "security",
    "securityhub.amazonaws.com": "security",
    "waf.amazonaws.com": "security",
    "logs.amazonaws.com": "logging",
    "cloudwatch.amazonaws.com": "monitoring",
    "sns.amazonaws.com": "messaging",
    "sqs.amazonaws.com": "messaging",
    "cloudformation.amazonaws.com": "infrastructure",
    "elasticloadbalancing.amazonaws.com": "networking",
    "route53.amazonaws.com": "networking",
    "vpc.amazonaws.com": "networking",
}


def _get_username(dot_message):
    """Extract the most useful username from useridentity, handling all identity types."""
    identity_type = dot_message.get("details.useridentity.type", "")

    # IAMUser — straightforward username
    username = dot_message.get("details.useridentity.username", "")
    if username:
        return username

    # AssumedRole — use the session name (often a human or lambda name)
    principal = dot_message.get("details.useridentity.principalid", "")
    if ":" in principal:
        return principal.split(":", 1)[1]

    # Root account
    if identity_type == "Root":
        return "root"

    # AWSService
    invokedby = dot_message.get("details.useridentity.invokedby", "")
    if invokedby:
        return invokedby

    # Fallback to ARN
    arn = dot_message.get("details.useridentity.arn", "")
    if arn:
        # Return just the resource portion: "user/name" or "role/MyRole"
        parts = arn.split(":")
        if len(parts) >= 6:
            return parts[-1]

    return "unknown"


class message(object):
    def __init__(self):
        """
        Generic normalization for AWS CloudTrail events.
        Sets summary, category, and tags from the consistent
        top-level CloudTrail fields present in all events.
        """
        self.registration = ["eventsource"]
        self.priority = 15

    def onMessage(self, message, metadata):
        # Only handle cloudtrail-sourced events
        if message.get("source") != "cloudtrail":
            return (message, metadata)

        dot_message = DotDict(message)
        eventsource = dot_message.get("details.eventsource", "")

        # Must look like an AWS event source
        if not eventsource.endswith(".amazonaws.com"):
            return (message, metadata)

        eventname = dot_message.get("details.eventname", "UNKNOWN")
        username = _get_username(dot_message)
        sourceip = dot_message.get("details.sourceipaddress", "")
        region = dot_message.get("details.awsregion", "")

        # --- Summary ---
        # Short, readable service name: "signin.amazonaws.com" → "signin"
        service = eventsource.replace(".amazonaws.com", "")
        parts = [f"{username} {eventname}"]
        if sourceip:
            parts.append(f"from {sourceip}")
        if region:
            parts.append(f"in {region}")
        message["summary"] = " ".join(parts)

        # --- Category ---
        message["category"] = CATEGORY_MAP.get(eventsource, service)

        # --- Tags ---
        tags = message.get("tags", [])
        tags.append("cloudtrail")
        tags.append("aws")

        if dot_message.get("details.readonly") is False:
            tags.append("write")
        elif dot_message.get("details.readonly") is True:
            tags.append("read")

        if dot_message.get("details.managementevent") is True:
            tags.append("management")

        # Tag the AWS service for easy filtering
        tags.append(service)

        message["tags"] = tags

        # --- Severity ---
        errorcode = str(dot_message.get("details.errorcode", ""))
        errormessage = str(dot_message.get("details.errormessage", ""))

        if errorcode or errormessage:
            message["severity"] = "WARNING"
            if "error" not in tags:
                tags.append("error")
            if errorcode:
                message["details"]["_errorcode"] = errorcode
            if errormessage:
                message["details"]["_errormessage"] = errormessage

        # Destructive actions get elevated severity
        destructive_prefixes = ("Delete", "Terminate", "Remove", "Deregister", "Revoke")
        if eventname.startswith(destructive_prefixes):
            if message["severity"] == "INFO":
                message["severity"] = "WARNING"

        # Root account usage is always notable
        identity_type = dot_message.get("details.useridentity.type", "")
        if identity_type == "Root":
            message["severity"] = "WARNING"
            if "root" not in tags:
                tags.append("root")

        # --- Authentication-specific enrichment ---
        if eventsource == "signin.amazonaws.com":
            console_login = dot_message.get("details.responseelements.consolelogin", "")
            if console_login:
                message["details"]["_login_result"] = console_login
                if console_login == "Failure":
                    message["severity"] = "WARNING"
                    tags.append("login-failure")
                elif console_login == "Success":
                    tags.append("login-success")

            mfa_used = dot_message.get("details.additionaleventdata.mfaused", "")
            if mfa_used:
                message["details"]["_mfa_used"] = mfa_used == "Yes"
                if mfa_used == "No":
                    tags.append("no-mfa")

        return (message, metadata)
