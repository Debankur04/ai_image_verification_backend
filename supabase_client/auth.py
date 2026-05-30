from supabase_client.supabase_init import supabase_public, supabase_admin
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError

def signup(email: str, password: str):
    response = supabase_admin.auth.sign_up({
        "email": email,
        "password": password
    })

    if response.user is None:
        return {
            "success": False,
            "message": "Signup failed"
        }

    return {
        "success": True,
        "message": "Signup successful. Verify email if required.",
        "user_id": response.user.id,
        "session": (
            {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
            if response.session
            else None
        )
    }


def signin(email: str, password: str):
    try:
        response = supabase_public.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user_id": response.user.id 
        }
    except AuthApiError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )


def signout():
    return supabase_public.auth.sign_out()
