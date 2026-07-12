from src.agent.run_authorization import RunAuthorization, authorization_from_payload


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
