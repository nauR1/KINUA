"""One UTC access policy, shared by login, requests and administration."""

import math
from datetime import datetime, timezone

from fastapi import HTTPException


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    )


def access_state(user, clinic, now=None):
    now = utc(now) if now else datetime.now(timezone.utc)
    user_expiry = utc(user.access_expires_at)
    user_start = utc(getattr(user, "access_starts_at", None))
    plan = None
    code = None
    expiry = user_expiry

    if user.role == "platform_admin":
        if not user.is_active:
            code = "account_disabled"
        expiry = None
    else:
        plan = ("demo" if clinic.is_demo else clinic.plan_code) if clinic else None
        lifetime = bool(clinic and not clinic.is_demo and clinic.plan_code == "lifetime")
        clinic_expiry = (
            utc(clinic.access_expires_at)
            if clinic and not clinic.is_demo and not lifetime
            else None
        )
        inherited_start = (
            utc(clinic.access_starts_at)
            if clinic and not clinic.is_demo and not lifetime
            else None
        )
        starts_at = user_start or inherited_start
        expiry = min([d for d in [user_expiry, clinic_expiry] if d], default=None)

        if not clinic or not clinic.is_active or (
            not clinic.is_demo and clinic.subscription_status == "suspended"
        ):
            code = "clinic_suspended"
        elif not user.is_active:
            code = "account_disabled"
        elif user_expiry and now >= user_expiry:
            code = "user_access_expired"
        elif clinic.is_demo:
            if user_start and now < user_start:
                code = "access_not_started"
        elif clinic.subscription_status == "cancelled":
            code = "subscription_cancelled"
        elif clinic.subscription_status == "expired" or (
            clinic_expiry and now >= clinic_expiry
        ):
            code = "subscription_expired"
        elif starts_at and now < starts_at:
            code = "access_not_started"

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
