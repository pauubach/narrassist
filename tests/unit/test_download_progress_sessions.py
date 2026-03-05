"""Guards de sesion para progreso de descargas NLP."""

from narrative_assistant.core.model_manager import (
    ModelType,
    _clear_download_progress,
    _update_download_progress,
    begin_download_progress_session,
    bind_download_progress_session,
    get_download_progress,
    rotate_download_progress_session,
)


def _cleanup_model_progress() -> None:
    for model_type in ModelType:
        _clear_download_progress(model_type)


def test_bound_session_update_is_applied():
    _cleanup_model_progress()
    token = begin_download_progress_session(ModelType.SPACY)

    with bind_download_progress_session(token):
        _update_download_progress(
            ModelType.SPACY,
            phase="queued",
            bytes_total=100,
        )

    progress = get_download_progress(ModelType.SPACY)
    assert progress is not None
    assert progress["phase"] == "queued"


def test_unbound_update_is_ignored_while_session_active():
    _cleanup_model_progress()
    token = begin_download_progress_session(ModelType.SPACY)
    _update_download_progress(
        ModelType.SPACY,
        phase="queued",
        bytes_total=100,
        progress_token=token,
    )

    # Sin token/contexto: debe ignorarse para evitar escrituras ambiguas.
    _update_download_progress(
        ModelType.SPACY,
        phase="completed",
        bytes_downloaded=100,
        bytes_total=100,
    )

    progress = get_download_progress(ModelType.SPACY)
    assert progress is not None
    assert progress["phase"] == "queued"


def test_stale_token_is_ignored_after_session_rotation():
    _cleanup_model_progress()
    token = begin_download_progress_session(ModelType.EMBEDDINGS)
    _update_download_progress(
        ModelType.EMBEDDINGS,
        phase="error",
        error_message="timeout",
        progress_token=token,
    )

    rotate_download_progress_session(ModelType.EMBEDDINGS, expected_token=token)

    # Escritura tardia de un worker viejo: debe ignorarse.
    _update_download_progress(
        ModelType.EMBEDDINGS,
        phase="completed",
        bytes_downloaded=100,
        bytes_total=100,
        progress_token=token,
    )

    progress = get_download_progress(ModelType.EMBEDDINGS)
    assert progress is not None
    assert progress["phase"] == "error"


def test_rotate_session_with_wrong_expected_token_keeps_current_session():
    _cleanup_model_progress()
    token = begin_download_progress_session(ModelType.TRANSFORMER_NER)
    current = rotate_download_progress_session(
        ModelType.TRANSFORMER_NER,
        expected_token=token + 999,
    )

    assert current == token

    # El token original sigue siendo valido.
    _update_download_progress(
        ModelType.TRANSFORMER_NER,
        phase="queued",
        bytes_total=100,
        progress_token=token,
    )
    progress = get_download_progress(ModelType.TRANSFORMER_NER)
    assert progress is not None
    assert progress["phase"] == "queued"
