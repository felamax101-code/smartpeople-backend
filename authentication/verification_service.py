from django.utils import timezone
from .models import VerificationRequest, CustomUser
from .utils import encrypt_id_number

MAX_ATTEMPTS = 5

# --- documents that require expiry date ---
EXPIRY_REQUIRED = {"passport", "national_id", "drivers_license"}


def _get_or_create_vr(user: CustomUser) -> VerificationRequest:
    vr, _ = VerificationRequest.objects.get_or_create(user=user)
    return vr


def submit_identity(
    user: CustomUser,
    id_type: str,
    id_number: str,
    id_front_url: str,
    id_back_url: str | None,
    selfie_url: str,
    document_expiry_date=None,
) -> dict:
    
    vr = _get_or_create_vr(user)

    # check attempt limit
    if vr.identity_attempt_count >= MAX_ATTEMPTS:
        vr.identity_status = "exhausted"
        vr.save()
        return {
            "success": False,
            "error": "Maximum submission attempts reached. Contact support."
        }

    # expiry date required for certain document types
    if id_type in EXPIRY_REQUIRED and not document_expiry_date:
        return {
            "success": False,
            "error": f"Expiry date is required for {id_type}"
        }

    # check document isn't already expired before submission
    if document_expiry_date and document_expiry_date < timezone.now().date():
        return {
            "success": False,
            "error": "Document is already expired. Please use a valid document."
        }

    # determine status â€” first submission or resubmission
    new_status = (
        "resubmitted" 
        if vr.identity_attempt_count > 0 
        else "pending"
    )

    # save â€” encrypt ID number before storing
    vr.identity_status = new_status
    vr.id_type = id_type
    vr.id_number = encrypt_id_number(id_number)
    vr.id_front = id_front_url
    vr.id_back = id_back_url
    vr.selfie = selfie_url
    vr.document_expiry_date = document_expiry_date
    vr.identity_rejection_reason = None  # clear previous rejection
    vr.identity_attempt_count += 1
    vr.save()

    return {
        "success": True,
        "status": new_status,
        "attempts_remaining": MAX_ATTEMPTS - vr.identity_attempt_count
    }


def submit_business(
    user: CustomUser,
    business_name: str,
    rc_number: str,
    business_address: str,
    cac_document_url: str,
) -> dict:

    vr = _get_or_create_vr(user)

    if vr.business_attempt_count >= MAX_ATTEMPTS:
        vr.business_status = "exhausted"
        vr.save()
        return {
            "success": False,
            "error": "Maximum submission attempts reached. Contact support."
        }

    new_status = (
        "resubmitted"
        if vr.business_attempt_count > 0
        else "pending"
    )

    vr.business_status = new_status
    vr.business_name = business_name
    vr.rc_number = rc_number
    vr.business_address = business_address
    vr.cac_document = cac_document_url
    vr.business_rejection_reason = None
    vr.business_attempt_count += 1
    vr.save()

    return {
        "success": True,
        "status": new_status,
        "attempts_remaining": MAX_ATTEMPTS - vr.business_attempt_count
    }


def review_identity(
    vr: VerificationRequest,
    action: str,
    reviewer: CustomUser,
    reason: str | None = None,
) -> dict:

    if action == "approve":
        vr.identity_status = "approved"
        vr.identity_rejection_reason = None
    elif action == "reject":
        if not reason:
            return {"success": False, "error": "Rejection reason is required"}
        vr.identity_status = "rejected"
        vr.identity_rejection_reason = reason
    else:
        return {"success": False, "error": "action must be approve or reject"}

    vr.identity_reviewed_by = reviewer
    vr.identity_reviewed_at = timezone.now()
    vr.save()

    return {"success": True, "status": vr.identity_status}


def review_business(
    vr: VerificationRequest,
    action: str,
    reviewer: CustomUser,
    reason: str | None = None,
) -> dict:

    if action == "approve":
        vr.business_status = "approved"
        vr.business_rejection_reason = None
    elif action == "reject":
        if not reason:
            return {"success": False, "error": "Rejection reason is required"}
        vr.business_status = "rejected"
        vr.business_rejection_reason = reason
    else:
        return {"success": False, "error": "action must be approve or reject"}

    vr.business_reviewed_by = reviewer
    vr.business_reviewed_at = timezone.now()
    vr.save()

    return {"success": True, "status": vr.business_status}


def unlock_attempts(vr: VerificationRequest, section: str) -> dict:
    """Staff manually unlocks exhausted accounts"""
    if section == "identity":
        vr.identity_attempt_count = 0
        vr.identity_status = "pending"
        vr.save()
    elif section == "business":
        vr.business_attempt_count = 0
        vr.business_status = "pending"
        vr.save()
    else:
        return {"success": False, "error": "section must be identity or business"}

    return {"success": True, "message": f"{section} attempts reset"}