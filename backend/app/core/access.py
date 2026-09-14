"""One UTC access policy, shared by login, requests and administration."""

import math
from datetime import datetime, timezone

from fastapi import HTTPException


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    )


def access_state(user, clinic, now=None):
    now = now or datetime.now(timezone.utc)
    expiry = utc(user.access_expires_at)
    plan = None
    code = None
    if not user.is_active:
        code = "account_disabled"
    if user.role != "platform_admin":
        plan = ("demo" if clinic.is_demo else clinic.plan_code) if clinic else None
        clinic_expiry = (
            utc(clinic.access_expires_at) if clinic and not clinic.is_demo else None
        )
        expiry = min([d for d in [expiry, clinic_expiry] if d], default=None)
        if not code:
            if user.access_expires_at and now >= utc(user.access_expires_at):
                code = "user_access_expired"
            elif (
                not clinic
                or not clinic.is_active
                or (not clinic.is_demo and clinic.subscription_status == "suspended")
            ):
                code = "clinic_suspended"
            elif clinic.is_demo:
                expiry = utc(user.access_expires_at)
            elif clinic.subscription_status == "cancelled":
                code = "subscription_cancelled"
            elif clinic.subscription_status == "expired" or (
                clinic_expiry and now >= clinic_expiry
            ):
                code = "subscription_expired"
            elif clinic.access_starts_at and now < utc(clinic.access_starts_at):
                code = "access_not_started"
    else:
        expiry = None
    return {
        "allowed": code is None,
        "is_demo": bool(clinic and clinic.is_demo),
        "code": code,
        "plan": plan,
        "expires_at": expiry.isoformat() if expiry else None,
        "days_remaining": max(0, math.ceil((expiry - now).total_seconds() / 86400))
        if expiry
        else None,
    }


def enforce_access(user, clinic):
    state = access_state(user, clinic)
    if not state["allowed"]:
        raise HTTPException(403, state)
    return state
