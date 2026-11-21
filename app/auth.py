"""Sign in with Google (OpenID Connect) and session helpers."""
import os
from typing import Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

oauth = OAuth()
if GOOGLE_CONFIGURED:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

router = APIRouter()


def get_optional_user(request: Request) -> Optional[dict]:
    """The signed-in user from the session cookie, or None."""
    return request.session.get("user")


def get_user(user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """Like get_optional_user, but refuses the request if nobody is signed in."""
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in with Google first.")
    return user


@router.get("/login")
async def login(request: Request):
    if not GOOGLE_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in isn't set up yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.",
        )
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse("/?login=failed")

    info = token.get("userinfo") or {}
    if not info.get("email") or not info.get("email_verified"):
        return RedirectResponse("/?login=unverified")

    # Only keep what the app needs. Google's tokens are never stored.
    request.session["user"] = {
        "email": info["email"].lower(),
        "name": info.get("name") or info["email"],
        "picture": info.get("picture"),
    }
    return RedirectResponse("/")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"signed_out": True}


@router.get("/me")
def me(user: Optional[dict] = Depends(get_optional_user)):
    return {"user": user, "google_configured": GOOGLE_CONFIGURED}