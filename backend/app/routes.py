from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from app.config import database_path
from app.controllers import auth, chat, database
from app.models.schemas import (
    AuthResponse,
    CheckInCreateRequest,
    CheckInResponse,
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    EventCreateRequest,
    EventResponse,
    ExerciseResponse,
    ExerciseHistoryCreateRequest,
    ExerciseHistoryResponse,
    ExerciseHistoryUpdateRequest,
    HealthResponse,
    LoginRequest,
    ProfileUpdateRequest,
    QuestionnaireRequest,
    QuestionnaireResponse,
    RegisterRequest,
    SettingsUpdateRequest,
    UserResponse,
)


router = APIRouter(prefix="/api")

EXERCISES = [
    {
        "id": "grounding-54321",
        "title": "5-4-3-2-1 grounding",
        "summary": "Move through your senses to reconnect with the present moment.",
        "steps": [
            "Notice five things you can see.",
            "Notice four things you can feel or touch.",
            "Notice three things you can hear.",
            "Notice two things you can smell, or two scents you enjoy.",
            "Notice one thing you can taste, or a taste you enjoy.",
        ],
    },
    {
        "id": "box-breathing",
        "title": "Four-count breathing",
        "summary": "Follow a quiet visual rhythm through four gentle breathing phases.",
        "steps": [
            "Breathe in gently.",
            "Pause only if comfortable.",
            "Breathe out gently.",
            "Rest before the next breath.",
        ],
    },
]


def _token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return authorization.split(" ", 1)[1].strip()


def current_user_id(token: Annotated[str, Depends(_token)]) -> str:
    try:
        return auth.user_id_for_token(token)
    except database.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok", "database": "ready"}


@router.post("/chat", response_model=ChatResponse)
def support_chat(payload: ChatRequest, user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    context, context_used = database.build_chat_context(database_path(), user_id)
    if chat.is_crisis_message(payload.message):
        return {
            "reply": chat.crisis_reply(),
            "model": "local-safety-response",
            "context_used": context_used,
            "crisis_response": True,
        }
    try:
        reply, model = chat.request_support_reply(
            payload.message,
            [item.model_dump() for item in payload.history],
            context,
        )
        return {
            "reply": reply,
            "model": model,
            "context_used": context_used,
            "crisis_response": False,
        }
    except chat.ChatConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except chat.ChatProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict:
    try:
        return auth.register(database_path(), payload.username, payload.display_name, payload.email, payload.password)
    except database.AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> dict:
    try:
        return auth.login(database_path(), payload.username, payload.password)
    except database.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/auth/me", response_model=UserResponse)
def me(user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    return database.get_user(database_path(), user_id)


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    user_id: Annotated[str, Depends(current_user_id)],
) -> dict:
    try:
        return database.update_user_profile(database_path(), user_id, payload.model_dump())
    except database.AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except database.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/settings", response_model=UserResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    user_id: Annotated[str, Depends(current_user_id)],
) -> dict:
    try:
        return database.update_user_settings(database_path(), user_id, payload.model_dump())
    except database.AccountConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except database.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: Annotated[str, Depends(_token)]) -> Response:
    auth.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/questionnaire", response_model=QuestionnaireResponse | None)
def read_questionnaire(user_id: Annotated[str, Depends(current_user_id)]) -> dict | None:
    return database.get_questionnaire(database_path(), user_id)


@router.put("/questionnaire", response_model=QuestionnaireResponse)
def update_questionnaire(payload: QuestionnaireRequest, user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    return database.save_questionnaire(database_path(), user_id, payload.model_dump())


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    return database.dashboard_snapshot(database_path(), user_id)


@router.get("/check-ins", response_model=list[CheckInResponse])
def check_ins(user_id: Annotated[str, Depends(current_user_id)], limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return database.list_checkins(database_path(), user_id, limit)


@router.post("/check-ins", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
def create_check_in(payload: CheckInCreateRequest, user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    return database.create_checkin(database_path(), user_id, payload.model_dump())


@router.get("/events", response_model=list[EventResponse])
def events(
    user_id: Annotated[str, Depends(current_user_id)],
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> list[dict]:
    return database.list_events(database_path(), user_id, month)


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateRequest, user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    return database.create_event(database_path(), user_id, payload.model_dump())


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_event(event_id: str, user_id: Annotated[str, Depends(current_user_id)]) -> Response:
    try:
        database.delete_event(database_path(), user_id, event_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except database.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/exercises", response_model=list[ExerciseResponse])
def exercises() -> list[dict]:
    return EXERCISES


@router.get("/exercise-history", response_model=list[ExerciseHistoryResponse])
def exercise_history(
    user_id: Annotated[str, Depends(current_user_id)],
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict]:
    return database.list_exercise_history(database_path(), user_id, limit)


@router.post("/exercise-history", response_model=ExerciseHistoryResponse, status_code=status.HTTP_201_CREATED)
def start_exercise(
    payload: ExerciseHistoryCreateRequest,
    user_id: Annotated[str, Depends(current_user_id)],
) -> dict:
    return database.create_exercise_history(database_path(), user_id, payload.exercise_id)


@router.patch("/exercise-history/{history_id}", response_model=ExerciseHistoryResponse)
def update_exercise(
    history_id: str,
    payload: ExerciseHistoryUpdateRequest,
    user_id: Annotated[str, Depends(current_user_id)],
) -> dict:
    try:
        return database.update_exercise_history(
            database_path(), user_id, history_id, payload.status, payload.reflection
        )
    except database.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/exercise-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_exercise_history(
    history_id: str,
    user_id: Annotated[str, Depends(current_user_id)],
) -> Response:
    try:
        database.delete_exercise_history(database_path(), user_id, history_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except database.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

