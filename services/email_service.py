import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from itsdangerous import URLSafeTimedSerializer
from config import settings


class EmailService:
    def __init__(self):
        self.serializer = URLSafeTimedSerializer(settings.secret_key)

    def generate_confirmation_token(self, email: str) -> str:
        """Generate email confirmation token"""
        return self.serializer.dumps(email, salt='email-confirm')

    def verify_confirmation_token(self, token: str, max_age: int = None) -> str:
        """Verify email confirmation token and return email"""
        if max_age is None:
            max_age = settings.email_confirmation_expire_minutes * 60

        try:
            email = self.serializer.loads(
                token,
                salt='email-confirm',
                max_age=max_age
            )
            return email
        except Exception:
            return None

    async def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send email using SMTP"""
        if not settings.smtp_username or not settings.smtp_password:
            print(f"Email would be sent to {to_email} with subject: {subject}")
            print(f"Content: {text_content or html_content}")
            return  # Skip actual sending if SMTP not configured

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.from_email
        message["To"] = to_email

        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                start_tls=True,
                username=settings.smtp_username,
                password=settings.smtp_password,
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            raise Exception(f"Failed to send email: {e}")

    async def send_confirmation_email(self, email: str, username: str, token: str):
        """Send email confirmation email"""
        confirmation_url = f"{settings.app_url}/auth/verify-email?token={token}"

        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Confirm Your Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #333; text-align: center;">Welcome to AI FastAPI App!</h1>
                <p style="color: #666; font-size: 16px;">Hi {{ username }},</p>
                <p style="color: #666; font-size: 16px;">
                    Thank you for registering with our AI FastAPI application. 
                    To complete your registration, please verify your email address by clicking the button below:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{ confirmation_url }}" 
                       style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, you can copy and paste this link into your browser:
                    <br><a href="{{ confirmation_url }}">{{ confirmation_url }}</a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    This link will expire in 24 hours for security reasons.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If you didn't create an account with us, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """)

        text_content = f"""
        Welcome to AI FastAPI App!
        
        Hi {username},
        
        Thank you for registering with our AI FastAPI application.
        To complete your registration, please verify your email address by visiting:
        
        {confirmation_url}
        
        This link will expire in 24 hours for security reasons.
        
        If you didn't create an account with us, you can safely ignore this email.
        """

        html_content = html_template.render(
            username=username,
            confirmation_url=confirmation_url
        )

        await self.send_email(
            to_email=email,
            subject="Confirm Your Email - AI FastAPI App",
            html_content=html_content,
            text_content=text_content
        )


# Dependency injection function
def get_email_service() -> EmailService:
    """Dependency injection function for email service"""
    return EmailService()
