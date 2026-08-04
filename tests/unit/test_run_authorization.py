from src.agent.run_authorization import (
    AuthorizationTarget,
    RunAuthorization,
    authorization_from_payload,
)


def test_authorization_from_payload_preserves_explicit_scope():
    authorization = authorization_from_payload(
        {
            "user_authorized": True,
            "authorization": {
                "target_account": "12345",
                "authorized_actions": ["close_card"],
                "declined_alternatives": ["product_change"],
                "huca_authorized": True,
            },
        }
    )

    assert authorization.target_account == "12345"
    assert authorization.permits("close_card") is True
    assert authorization.permits("request_credit_refund") is False
    assert authorization.huca_authorized is True


def test_unstructured_user_authorized_does_not_infer_actions():
    authorization = authorization_from_payload({"user_authorized": True})

    assert authorization == RunAuthorization(user_authorized=True)
    assert authorization.permits("close_card") is False


def test_structured_targets_keep_permissions_target_scoped():
    authorization = authorization_from_payload(
        {
            "user_authorized": True,
            "authorization": {
                "targets": [
                    {
                        "key": "target-a",
                        "display": "synthetic service A",
                        "authorized_actions": ["close_card"],
                    },
                    {
                        "key": "target-b",
                        "display": "synthetic service B",
                        "authorized_actions": ["request_credit_refund"],
                    },
                ],
                "authorized_actions": ["close_card", "request_credit_refund"],
            },
        }
    )

    assert authorization.permits("close_card", "target-a") is True
    assert authorization.permits("close_card", "target-b") is False
    assert authorization.permits("request_credit_refund", "target-a") is False
    assert authorization.authorized_actions == []
    assert authorization.target_account is None
    assert authorization.targets[0] == AuthorizationTarget(
        key="target-a",
        display="synthetic service A",
        authorized_actions=["close_card"],
    )


def test_legacy_permissions_normalize_to_exactly_one_target():
    authorization = RunAuthorization(
        target_account="synthetic service",
        authorized_actions=["close_card"],
        user_authorized=True,
    )

    assert len(authorization.targets) == 1
    assert authorization.targets[0].key == "legacy-target"
    assert authorization.permits("close_card") is True
