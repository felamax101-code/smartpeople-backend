#profile report

from django.utils import timezone
from django.conf import settings
from .models import ProfileReport, ReportAppeal
from .models import CustomUser
from .notification_service import notify
from feed.models import Post,PostReport

THRESHOLDS = settings.REPORT_THRESHOLDS


def submit_report(
    reporter: CustomUser,
    target: CustomUser,
    reason: str,
    description: str | None
) -> dict:

    # cannot report yourself
    if reporter == target:
        return {"success": False, "error": "You cannot report yourself"}

    # duplicate report check
    if reason=="Other":
        reason=description
    if ProfileReport.objects.filter(
        reporter=reporter,
        target=target,
        reason=reason
    ).exists():
        return {
            "success": False,
            "error": "You have already reported this user for this reason"
        }

    # description required for "other"
    if reason == "other" and not description:
        return {"success": False, "error": "Description is required for 'other' reason"}

    report = ProfileReport.objects.create(
        reporter=reporter,
        target=target,
        reason=reason,
        description=description
    )

    # check thresholds
    total_reports = ProfileReport.objects.filter(
        target=target,
        status="pending"
    ).count()

    _handle_thresholds(target, total_reports)

    return {"success": True, "message": "Report submitted. Our team will review it."}




def submit_post_report(
    reporter: CustomUser,
    post: Post,
    reason: str,
    description: str | None
) -> dict:

    # cannot report yourself
    # if reporter == target:
    #     return {"success": False, "error": "You cannot report yourself"}

    # duplicate report check
    if reason=="Other":
        reason=description
    if PostReport.objects.filter(
        reporter=reporter,
        post=post,
        reason=reason
    ).exists():
        return {
            "success": False,
            "error": "You have already reported this post for this reason"
        }

    # description required for "other"
    if reason == "other" and not description:
        return {"success": False, "error": "Description is required for 'other' reason"}

    report = PostReport.objects.create(
        reporter=reporter,
        post=post,
        reason=reason,
        description=description
    )

    # check thresholds
    total_reports = PostReport.objects.filter(
        post=post,
        status="pending"
    ).count()

    _handle_thresholds(post, total_reports)

    return {"success": True, "message": "Report submitted. Our team will review it."}



def review_report(
    report: ProfileReport,
    action: str,
    reviewer: CustomUser
) -> dict:

    valid_actions = ("none", "warn", "suspend", "ban")
    if action not in valid_actions:
        return {"success": False, "error": f"action must be one of {valid_actions}"}

    report.status = "reviewed"
    report.action_taken = action
    report.reviewed_by = reviewer
    report.reviewed_at = timezone.now()
    report.save()

    # apply action to target user
    target = report.target
    _apply_action(target, action)

    return {"success": True, "action": action}


def dismiss_report(report: ProfileReport, reviewer: CustomUser) -> dict:
    report.status = "dismissed"
    report.action_taken = "none"
    report.reviewed_by = reviewer
    report.reviewed_at = timezone.now()
    report.save()
    return {"success": True, "message": "Report dismissed"}


def submit_appeal(
    user: CustomUser,
    report: ProfileReport,
    message: str
) -> dict:

    # only the target can appeal
    if user != report.target:
        return {"success": False, "error": "You can only appeal reports against you"}

    # only suspended/banned accounts can appeal
    if report.action_taken not in ("suspend", "ban"):
        return {"success": False, "error": "Only suspended or banned accounts can appeal"}

    # one appeal per report
    if hasattr(report, "appeal"):
        return {"success": False, "error": "You have already submitted an appeal for this report"}

    appeal = ReportAppeal.objects.create(
        report=report,
        user=user,
        message=message
    )

    # notify staff
    from authentication.tasks import send_generic_email
    _notify_staff_appeal(user.username)

    return {"success": True, "message": "Appeal submitted. Our team will review it."}


def review_appeal(
    appeal: ReportAppeal,
    action: str,
    reviewer: CustomUser
) -> dict:

    if action not in ("accepted", "rejected"):
        return {"success": False, "error": "action must be accepted or rejected"}

    appeal.status = action
    appeal.reviewed_by = reviewer
    appeal.reviewed_at = timezone.now()
    appeal.save()

    user = appeal.user

    if action == "accepted":
        # lift the suspension/ban
        user.is_locked = False
        user.save()

        notify(
            recipient=user,
            notification_type="appeal_update",
            title="Appeal Accepted",
            body="Your appeal has been accepted and your account has been restored.",
            send_push=True,
            send_email=True,
        )
    else:
        notify(
            recipient=user,
            notification_type="appeal_update",
            title="Appeal Rejected",
            body="Your appeal has been reviewed and the decision stands.",
            send_push=True,
            send_email=True,
        )

    return {"success": True, "status": action}




def _handle_thresholds(target: CustomUser, total_reports: int) -> None:
    from authentication.tasks import notify_staff_flagged_account

    for threshold, action in sorted(THRESHOLDS.items()):
        if total_reports == threshold:
            if action == "flagged":
                notify_staff_flagged_account(
                    target.username,
                    total_reports
                )
            elif action == "suspended":
                target.is_locked = True
                target.save()
                notify_staff_flagged_account(
                    target.username,
                    total_reports
                )
                notify(
                    recipient=target,
                    notification_type="account_suspended",
                    title="Account Suspended",
                    body="Your account has been suspended pending review due to multiple reports.",
                    send_push=True,
                    send_email=True,
                )


def _apply_action(target: CustomUser, action: str) -> None:
    if action == "warn":
        notify(
            recipient=target,
            notification_type="account_warning",
            title="Account Warning",
            body="Your account has received a warning. Please review our community guidelines.",
            send_push=True,
            send_email=True,
        )

    elif action == "suspend":
        target.is_locked = True
        target.save()
        notify(
            recipient=target,
            notification_type="account_suspended",
            title="Account Suspended",
            body="Your account has been suspended. You may appeal this decision.",
            data={"can_appeal": "true"},
            send_push=True,
            send_email=True,
        )

    elif action == "ban":
        target.is_locked = True
        target.is_active = False
        target.save()
        notify(
            recipient=target,
            notification_type="account_suspended",
            title="Account Banned",
            body="Your account has been permanently banned for violating our community guidelines.",
            send_push=True,
            send_email=True,
        )


def _notify_staff_appeal(username: str) -> None:
    from authentication.tasks import notify_staff_flagged_account
    notify_staff_flagged_account(username, 0)