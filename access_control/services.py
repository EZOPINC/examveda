"""Evaluate publication, public access and future entitlement requirements.

Content and exam views use one fail-closed policy. Payment and entitlement
storage are deliberately absent; restricted resources stay inaccessible until
a later approved feature supplies a verified entitlement lookup.
"""


def user_has_entitlement(user, entitlement_code):
    """Return false until an approved entitlement store can verify a grant.

    Payment callbacks must never be substituted for this server-side lookup.
    The future paid-access phase can implement the lookup against persisted,
    verified grants without moving checks into templates or browser state.
    """
    return False


def user_can_access(
    user,
    *,
    is_published,
    is_public,
    entitlement_code=None,
):
    """Allow published public resources or a verified named entitlement.

    Unpublished resources and restricted resources without a named entitlement
    fail closed for anonymous and authenticated users alike.
    """
    if not is_published:
        return False
    if is_public:
        return True
    if not entitlement_code or not getattr(user, "is_authenticated", False):
        return False
    return user_has_entitlement(user, entitlement_code)
