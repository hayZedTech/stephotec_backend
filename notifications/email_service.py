import logging
import threading
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send branded HTML emails for Stephotec Computer Technologies Ltd."""

    @staticmethod
    def _dispatch_send(msg, subject, to_email):
        try:
            msg.send(fail_silently=False)
            logger.info(f"Email '{subject}' successfully sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")

    @classmethod
    def _send_email(cls, to_email, subject, html_content, async_send=True):
        if not to_email:
            logger.warning("No recipient email provided for EmailService.")
            return False

        text_content = strip_tags(html_content)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Stephotec Computer Technologies Ltd <info@stephotec.com>")

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email],
            )
            msg.attach_alternative(html_content, "text/html")

            if async_send:
                t = threading.Thread(target=cls._dispatch_send, args=(msg, subject, to_email), daemon=True)
                t.start()
            else:
                cls._dispatch_send(msg, subject, to_email)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize email to {to_email}: {str(e)}")
            return False

    @classmethod
    def send_password_reset_email(cls, user, reset_url):
        subject = "Password Reset Request — Stephotec Computer Technologies Ltd"
        full_name = user.get_full_name() or user.username

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; padding-bottom: 24px; border-bottom: 2px solid #7c3aed; }}
            .brand {{ font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: 0.5px; }}
            .subbrand {{ font-size: 11px; font-weight: 700; color: #7c3aed; letter-spacing: 1px; margin-top: 2px; }}
            .content {{ padding: 28px 0; font-size: 15px; line-height: 1.6; }}
            .btn {{ display: inline-block; background-color: #7c3aed; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none; margin: 20px 0; font-size: 15px; text-align: center; }}
            .btn:hover {{ background-color: #6d28d9; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 20px; font-size: 12px; color: #64748b; text-align: center; line-height: 1.5; }}
            .warning {{ background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; font-size: 13px; color: #991b1b; margin-top: 16px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">COMPUTER TECHNOLOGIES LTD</div>
            </div>
            <div class="content">
              <p>Hello <strong>{full_name}</strong>,</p>
              <p>We received a request to reset your password for your Stephotec Student Account (<strong>{user.username}</strong>).</p>
              <p>Click the button below to reset your password. This link will expire in 24 hours:</p>
              <div style="text-align: center;">
                <a href="{reset_url}" class="btn" target="_blank">Reset Password Now</a>
              </div>
              <p>If the button above does not work, copy and paste the following link into your browser:</p>
              <p style="word-break: break-all; font-size: 13px; color: #2563eb;"><a href="{reset_url}">{reset_url}</a></p>
              <div class="warning">
                <strong>Security Alert:</strong> If you did not request a password reset, please ignore this email or contact support immediately. Your account remains secure.
              </div>
            </div>
            <div class="footer">
              <p><strong>Stephotec Computer Technologies Ltd</strong><br/>
              info@stephotec.com | +234 802 250 8370 | WhatsApp: +234 703 563 1513</p>
            </div>
          </div>
        </body>
        </html>
        """
        return cls._send_email(user.email, subject, html_content)

    @classmethod
    def send_welcome_account_email(cls, user, temp_password, activation_url):
        subject = "Welcome to Stephotec Computer Technologies Ltd — Student Portal Account"
        full_name = user.get_full_name() or user.username

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; padding-bottom: 24px; border-bottom: 2px solid #2563eb; }}
            .brand {{ font-size: 22px; font-weight: 800; color: #0f172a; }}
            .subbrand {{ font-size: 11px; font-weight: 700; color: #2563eb; letter-spacing: 1px; }}
            .cred-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 20px 0; font-family: monospace; font-size: 14px; border: 1px solid #cbd5e1; }}
            .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 700; text-decoration: none; margin: 16px 0; text-align: center; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 20px; font-size: 12px; color: #64748b; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">COMPUTER TECHNOLOGIES LTD</div>
            </div>
            <div class="content">
              <p>Welcome <strong>{full_name}</strong>,</p>
              <p>Your official student account has been created on the Stephotec Portal. Below are your login credentials:</p>
              <div class="cred-box">
                <strong>Student ID / Username:</strong> {user.username}<br/>
                <strong>Temporary Password:</strong> {temp_password}
              </div>
              <p>Please click the link below to activate your profile and change your temporary password:</p>
              <div style="text-align: center;">
                <a href="{activation_url}" class="btn" target="_blank">Activate Your Profile</a>
              </div>
            </div>
            <div class="footer">
              <p><strong>Stephotec Computer Technologies Ltd</strong><br/>info@stephotec.com | +234 802 250 8370</p>
            </div>
          </div>
        </body>
        </html>
        """
        return cls._send_email(user.email, subject, html_content)

    @classmethod
    def send_notification_email(cls, user, title, message):
        if not user.email:
            return False

        subject = f"{title} — Stephotec Portal Notification"
        full_name = user.get_full_name() or user.username

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; }}
            .header {{ text-align: center; padding-bottom: 20px; border-bottom: 2px solid #7c3aed; }}
            .brand {{ font-size: 20px; font-weight: 800; color: #0f172a; }}
            .subbrand {{ font-size: 10px; font-weight: 700; color: #7c3aed; letter-spacing: 1px; }}
            .content {{ padding: 24px 0; font-size: 15px; line-height: 1.6; }}
            .footer {{ border-top: 1px solid #f1f5f9; padding-top: 16px; font-size: 12px; color: #64748b; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <div class="brand">STEPHOTEC</div>
              <div class="subbrand">COMPUTER TECHNOLOGIES LTD</div>
            </div>
            <div class="content">
              <p>Hello <strong>{full_name}</strong>,</p>
              <h3 style="color: #7c3aed; margin-top: 0;">{title}</h3>
              <p>{message}</p>
            </div>
            <div class="footer">
              <p>Stephotec Computer Technologies Ltd | info@stephotec.com</p>
            </div>
          </div>
        </body>
        </html>
        """
        return cls._send_email(user.email, subject, html_content)
