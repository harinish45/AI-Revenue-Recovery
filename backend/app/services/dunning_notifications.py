"""Automated Dunning Notification Sequences & Multi-lingual Messaging.

Provides localized email and SMS templates for graceful payment failure notifications,
card expiration warnings, urgency escalations, and final attempt notices.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Customer, DunningNotification, RecoveryCase
from ..services.audit_service import log_event
from ..utils.time import utcnow

logger = logging.getLogger("recoverai.notifications")


class NotificationTemplate(str, Enum):
    GRACE_PERIOD = "grace_period"
    CARD_EXPIRATION = "card_expiration_notice"
    URGENT_RETRY_FAILED = "urgent_retry_failed"
    FINAL_ATTEMPT = "final_attempt"


@dataclass(frozen=True)
class LocalizedMessage:
    subject: str
    body: str


# Multi-lingual notification templates (EN, ES, FR, DE, HI, JA)
TEMPLATES: Dict[str, Dict[str, LocalizedMessage]] = {
    NotificationTemplate.GRACE_PERIOD.value: {
        "en": LocalizedMessage(
            subject="Quick update regarding your {brand_name} subscription payment",
            body=(
                "Hi {customer_name},\n\n"
                "We attempted to renew your subscription for {currency} {amount}, but your bank couldn't "
                "complete the transaction ({failure_reason}).\n\n"
                "Don't worry — your access remains uninterrupted during this {grace_days}-day grace period.\n\n"
                "You can securely verify or update your payment details here:\n"
                "{update_url}\n\n"
                "Best regards,\nThe {brand_name} Billing Team"
            ),
        ),
        "es": LocalizedMessage(
            subject="Actualización sobre el pago de su suscripción a {brand_name}",
            body=(
                "Hola {customer_name},\n\n"
                "Intentamos renovar su suscripción por {currency} {amount}, pero el banco no pudo "
                "completar la transacción ({failure_reason}).\n\n"
                "No se preocupe: su servicio continúa activo durante el periodo de gracia de {grace_days} días.\n\n"
                "Puede actualizar su método de pago de forma segura aquí:\n"
                "{update_url}\n\n"
                "Saludos cordiales,\nEquipo de Facturación de {brand_name}"
            ),
        ),
        "fr": LocalizedMessage(
            subject="Information concernant le paiement de votre abonnement {brand_name}",
            body=(
                "Bonjour {customer_name},\n\n"
                "Nous avons tenté de renouveler votre abonnement de {currency} {amount}, mais votre banque n'a pas "
                "pu finaliser l'opération ({failure_reason}).\n\n"
                "Vos services restent pleinement accessibles pendant votre période de grâce de {grace_days} jours.\n\n"
                "Veuillez mettre à jour votre moyen de paiement ici :\n"
                "{update_url}\n\n"
                "Cordialement,\nL'équipe {brand_name}"
            ),
        ),
        "de": LocalizedMessage(
            subject="Wichtige Information zu Ihrer {brand_name}-Zahlung",
            body=(
                "Hallo {customer_name},\n\n"
                "wir konnten Ihre Abonnementverlängerung über {currency} {amount} leider nicht abbuchen ({failure_reason}).\n\n"
                "Ihr Zugang bleibt während der {grace_days}-tägigen Schonfrist uneingeschränkt aktiv.\n\n"
                "Bitte aktualisieren Sie Ihre Zahlungsdaten hier:\n"
                "{update_url}\n\n"
                "Mit freundlichen Grüßen,\nIhr {brand_name} Team"
            ),
        ),
        "hi": LocalizedMessage(
            subject="आपकी {brand_name} सदस्यता भुगतान के संबंध में जरूरी जानकारी",
            body=(
                "नमस्ते {customer_name},\n\n"
                "हमने आपकी {currency} {amount} की सदस्यता का नवीनीकरण करने का प्रयास किया, लेकिन बैंक द्वारा "
                "लेनदेन पूरा नहीं हो सका ({failure_reason})।\n\n"
                "चिंता न करें — अगले {grace_days} दिनों की छूट अवधि में आपकी सेवा सुचारू रहेगी।\n\n"
                "कृपया यहां अपने भुगतान विवरण सुरक्षित रूप से अपडेट करें:\n"
                "{update_url}\n\n"
                "सादर,\n{brand_name} बिलिंग टीम"
            ),
        ),
        "ja": LocalizedMessage(
            subject="【{brand_name}】サブスクリプションのお支払いに関するご案内",
            body=(
                "{customer_name} 様\n\n"
                "いつもご利用いただきありがとうございます。\n"
                "{currency} {amount} のお引き落としを試行いたしましたが、決済を完了できませんでした（{failure_reason}）。\n\n"
                "現在{grace_days}日間の猶予期間中のため、サービスは通常通りご利用いただけます。\n\n"
                "下記リンクよりお支払い情報のご確認・更新をお願いいたします：\n"
                "{update_url}\n\n"
                "{brand_name} サポートチーム"
            ),
        ),
    },
    NotificationTemplate.CARD_EXPIRATION.value: {
        "en": LocalizedMessage(
            subject="Action Required: Your card on file for {brand_name} has expired",
            body=(
                "Hi {customer_name},\n\n"
                "The payment card registered for your {brand_name} subscription has expired.\n\n"
                "To prevent any service disruption, please update your card details:\n"
                "{update_url}\n\n"
                "Thank you,\nThe {brand_name} Team"
            ),
        ),
        "es": LocalizedMessage(
            subject="Acción requerida: Su tarjeta registrada en {brand_name} ha caducado",
            body=(
                "Hola {customer_name},\n\n"
                "La tarjeta asociada a su suscripción de {brand_name} ha expirado.\n\n"
                "Para evitar interrupciones en el servicio, actualice los datos de su tarjeta aquí:\n"
                "{update_url}\n\n"
                "Gracias,\nEl equipo de {brand_name}"
            ),
        ),
        "fr": LocalizedMessage(
            subject="Action requise : Votre carte bancaire pour {brand_name} a expiré",
            body=(
                "Bonjour {customer_name},\n\n"
                "La carte bancaire associée à votre compte {brand_name} est arrivée à expiration.\n\n"
                "Afin d'éviter toute coupure de service, merci d'actualiser vos coordonnées bancaires :\n"
                "{update_url}\n\n"
                "Merci,\nL'équipe {brand_name}"
            ),
        ),
        "de": LocalizedMessage(
            subject="Handlung erforderlich: Ihre hinterlegte Zahlungskarte für {brand_name} ist abgelaufen",
            body=(
                "Hallo {customer_name},\n\n"
                "Ihre für {brand_name} hinterlegte Zahlungskarte ist abgelaufen.\n\n"
                "Bitte aktualisieren Sie Ihre Kartendaten, um eine Unterbrechung des Dienstes zu vermeiden:\n"
                "{update_url}\n\n"
                "Vielen Dank,\nIhr {brand_name} Team"
            ),
        ),
        "hi": LocalizedMessage(
            subject="कार्रवाई आवश्यक: {brand_name} के लिए आपका कार्ड समाप्त हो चुका है",
            body=(
                "नमस्ते {customer_name},\n\n"
                "आपकी {brand_name} सदस्यता के लिए पंजीकृत कार्ड की वैधता समाप्त हो गई है।\n\n"
                "सेवा में किसी भी रुकावट से बचने के लिए, कृपया कार्ड विवरण अपडेट करें:\n"
                "{update_url}\n\n"
                "धन्यवाद,\n{brand_name} टीम"
            ),
        ),
        "ja": LocalizedMessage(
            subject="【要対応】ご登録クレジットカードの有効期限切れのお知らせ",
            body=(
                "{customer_name} 様\n\n"
                "ご登録いただいているクレジットカードの有効期限が切れております。\n\n"
                "サービス停止を防ぐため、速やかにカード情報の更新をお願いいたします：\n"
                "{update_url}\n\n"
                "{brand_name} サポートチーム"
            ),
        ),
    },
    NotificationTemplate.URGENT_RETRY_FAILED.value: {
        "en": LocalizedMessage(
            subject="Urgent: Second payment attempt failed for {brand_name}",
            body=(
                "Hi {customer_name},\n\n"
                "We attempted to charge {currency} {amount} for your subscription again today, but the transaction "
                "could not be completed.\n\n"
                "Please update your payment method immediately to keep your account active:\n"
                "{update_url}\n\n"
                "Best,\nThe {brand_name} Team"
            ),
        ),
        "es": LocalizedMessage(
            subject="Urgente: Segundo intento de cobro fallido en {brand_name}",
            body=(
                "Hola {customer_name},\n\n"
                "Hemos reintentado el cobro de {currency} {amount} hoy, pero no se ha podido procesar.\n\n"
                "Por favor, actualice su método de pago para mantener su cuenta activa:\n"
                "{update_url}\n\n"
                "Atentamente,\nEquipo de {brand_name}"
            ),
        ),
        "fr": LocalizedMessage(
            subject="Urgent : Le deuxième essai de paiement a échoué pour {brand_name}",
            body=(
                "Bonjour {customer_name},\n\n"
                "Notre nouvelle tentative de prélèvement de {currency} {amount} n'a pas pu aboutir.\n\n"
                "Merci de régulariser votre moyen de paiement au plus vite :\n"
                "{update_url}\n\n"
                "L'équipe {brand_name}"
            ),
        ),
        "de": LocalizedMessage(
            subject="Dringend: Zweiter Zahlungsversuch für {brand_name} fehlgeschlagen",
            body=(
                "Hallo {customer_name},\n\n"
                "der erneute Abbuchungsversuch über {currency} {amount} war leider nicht erfolgreich.\n\n"
                "Bitte aktualisieren Sie Ihre Zahlungsart umgehend, um Ihren Account aktiv zu halten:\n"
                "{update_url}\n\n"
                "Ihr {brand_name} Team"
            ),
        ),
        "hi": LocalizedMessage(
            subject="अति आवश्यक: {brand_name} का दूसरा भुगतान प्रयास विफल रहा",
            body=(
                "नमस्ते {customer_name},\n\n"
                "आज हमने फिर से {currency} {amount} के भुगतान का प्रयास किया, लेकिन सफलता नहीं मिली।\n\n"
                "खाता सक्रिय रखने के लिए कृपया तुरंत अपनी भुगतान विधि अपडेट करें:\n"
                "{update_url}\n\n"
                "{brand_name} टीम"
            ),
        ),
        "ja": LocalizedMessage(
            subject="【重要】再決済失敗のお知らせ - {brand_name}",
            body=(
                "{customer_name} 様\n\n"
                "本日、再決済（{currency} {amount}）を試行いたしましたが、処理を完了できませんでした。\n\n"
                "アカウントの一時停止を避けるため、お早めにお支払い方法の更新をお願いいたします：\n"
                "{update_url}\n\n"
                "{brand_name} サポートチーム"
            ),
        ),
    },
    NotificationTemplate.FINAL_ATTEMPT.value: {
        "en": LocalizedMessage(
            subject="Final Notice: Your {brand_name} subscription will be suspended in 48 hours",
            body=(
                "Hi {customer_name},\n\n"
                "This is our final notice regarding your past-due balance of {currency} {amount}.\n\n"
                "Unless an updated payment method is provided within 48 hours, your subscription will be "
                "suspended and access will be revoked.\n\n"
                "Restore your access now:\n"
                "{update_url}\n\n"
                "The {brand_name} Billing Team"
            ),
        ),
        "es": LocalizedMessage(
            subject="Aviso final: Su suscripción a {brand_name} será suspendida en 48 horas",
            body=(
                "Hola {customer_name},\n\n"
                "Este es el aviso final sobre su saldo pendiente de {currency} {amount}.\n\n"
                "Si no actualiza su método de pago en 48 horas, su suscripción será suspendida.\n\n"
                "Evite la suspensión aquí:\n"
                "{update_url}\n\n"
                "Equipo de Facturación de {brand_name}"
            ),
        ),
        "fr": LocalizedMessage(
            subject="Dernier avis : Votre abonnement {brand_name} sera suspendu dans 48 heures",
            body=(
                "Bonjour {customer_name},\n\n"
                "Ceci est notre dernier rappel concernant votre impayé de {currency} {amount}.\n\n"
                "Sans mise à jour de vos coordonnées bancaires sous 48h, votre abonnement sera résilié.\n\n"
                "Régulariser maintenant :\n"
                "{update_url}\n\n"
                "L'équipe {brand_name}"
            ),
        ),
        "de": LocalizedMessage(
            subject="Letzte Mahnung: Ihr {brand_name}-Abonnement wird in 48 Stunden gesperrt",
            body=(
                "Hallo {customer_name},\n\n"
                "dies ist die letzte Erinnerung bezüglich Ihres offenen Betrags von {currency} {amount}.\n\n"
                "Ohne Aktualisierung Ihrer Zahlungsdaten wird Ihr Zugang in 48 Stunden deaktiviert.\n\n"
                "Jetzt Zugang sichern:\n"
                "{update_url}\n\n"
                "Ihr {brand_name} Team"
            ),
        ),
        "hi": LocalizedMessage(
            subject="अंतिम सूचना: आपकी {brand_name} सदस्यता 48 घंटों में निलंबित कर दी जाएगी",
            body=(
                "नमस्ते {customer_name},\n\n"
                "यह आपके बकाया {currency} {amount} के संबंध में अंतिम सूचना है।\n\n"
                "यदि अगले 48 घंटों में भुगतान विधि अपडेट नहीं की गई, तो आपकी सदस्यता समाप्त हो जाएगी।\n\n"
                "तुरंत नवीनीकरण करें:\n"
                "{update_url}\n\n"
                "{brand_name} बिलिंग टीम"
            ),
        ),
        "ja": LocalizedMessage(
            subject="【最終通知】48時間後にアカウントが停止されます - {brand_name}",
            body=(
                "{customer_name} 様\n\n"
                "未納金額（{currency} {amount}）に関する最終のご案内です。\n\n"
                "48時間以内にお支払い方法のご更新が確認できない場合、サブスクリプションは停止されます。\n\n"
                "下記より今すぐお手続きいただけます：\n"
                "{update_url}\n\n"
                "{brand_name} 請求管理部"
            ),
        ),
    },
}


def render_template(
    template: NotificationTemplate,
    locale: str,
    context: Dict[str, Any],
) -> LocalizedMessage:
    """Render localized template with given variable dictionary."""
    template_variants = TEMPLATES.get(template.value, {})
    chosen_locale = locale if locale in template_variants else "en"
    raw_message = template_variants.get(chosen_locale, template_variants["en"])

    default_context = {
        "brand_name": "RecoverAI",
        "customer_name": "Valued Subscriber",
        "currency": "INR",
        "amount": "0.00",
        "failure_reason": "Payment issue",
        "grace_days": str(settings.DUNNING_GRACE_PERIOD_DAYS),
        "update_url": "https://billing.recoverai.com/update-payment",
    }
    merged_context = {**default_context, **context}

    rendered_subject = raw_message.subject.format(**merged_context)
    rendered_body = raw_message.body.format(**merged_context)

    return LocalizedMessage(subject=rendered_subject, body=rendered_body)


def send_dunning_notification(
    db: Session,
    case: RecoveryCase,
    template: NotificationTemplate,
    sequence_step: int,
    locale: Optional[str] = None,
    channel: str = "email",
) -> DunningNotification:
    """Create, simulate dispatch, and record an automated dunning notification."""
    customer = db.query(Customer).filter(Customer.id == case.customer_id).first()
    recipient = customer.email if customer and customer.email else "customer@example.com"
    customer_name = customer.name if customer and customer.name else case.customer_name

    context = {
        "customer_name": customer_name,
        "amount": f"{case.amount_at_risk:.2f}",
        "currency": "INR",
        "failure_reason": case.reason or "Card verification required",
        "grace_days": str(settings.DUNNING_GRACE_PERIOD_DAYS),
        "update_url": f"https://pay.recoverai.com/c/{case.id}/update",
    }

    target_locale = locale or settings.DEFAULT_LOCALE
    rendered = render_template(template, target_locale, context)

    notification = DunningNotification(
        case_id=case.id,
        sequence_step=sequence_step,
        template_name=template.value,
        locale=target_locale,
        channel=channel,
        recipient=recipient,
        subject=rendered.subject,
        content=rendered.body,
        status="delivered",
        sent_at=utcnow(),
    )
    db.add(notification)

    log_event(
        db=db,
        case_id=case.id,
        event_type="dunning_notification_sent",
        actor="dunning_sequencer",
        decision=template.value,
        reason=f"Sequence step #{sequence_step} dispatched to {recipient} ({channel}/{target_locale}).",
        action=f"send_{template.value}",
        result="delivered",
    )
    return notification
