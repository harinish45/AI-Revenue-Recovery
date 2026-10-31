from sqlalchemy.orm import Session

from app.models import Customer, RecoveryCase
from app.services.dunning_notifications import (
    NotificationTemplate,
    render_template,
    send_dunning_notification,
)


def test_render_all_templates_and_locales():
    locales = ["en", "es", "fr", "de", "hi", "ja"]
    templates = [
        NotificationTemplate.GRACE_PERIOD,
        NotificationTemplate.CARD_EXPIRATION,
        NotificationTemplate.URGENT_RETRY_FAILED,
        NotificationTemplate.FINAL_ATTEMPT,
    ]
    context = {
        "customer_name": "Test User",
        "amount": "99.00",
        "currency": "USD",
        "brand_name": "RecoverAI",
    }

    for tmpl in templates:
        for loc in locales:
            msg = render_template(tmpl, loc, context)
            assert msg.subject
            assert msg.body
            assert (
                "Test User" in msg.body or loc == "ja"
            )  # Japanese templates format name differently
            assert "99.00" in msg.body or "RecoverAI" in msg.body


def test_send_dunning_notification_records_db(db_session: Session):
    customer = Customer(
        id="cust_notif_01",
        name="Elena Rostova",
        email="elena@example.com",
    )
    case = RecoveryCase(
        id="RC-NOTIF-01",
        customer_id=customer.id,
        customer_name=customer.name,
        amount_at_risk=249.0,
        recovery_status="pending",
    )
    db_session.add_all([customer, case])
    db_session.commit()

    notif = send_dunning_notification(
        db=db_session,
        case=case,
        template=NotificationTemplate.GRACE_PERIOD,
        sequence_step=1,
        locale="en",
    )
    db_session.commit()

    assert notif.id.startswith("NOTIF-")
    assert notif.recipient == "elena@example.com"
    assert notif.sequence_step == 1
    assert notif.status == "delivered"
