from malath.i18n import TRANSLATIONS


def test_public_home_describes_malath(client):
    response = client.get("/?lang=en")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Malath" in body
    assert "Protect Your Documents" in body
    assert "/register?lang=en" in body


def test_unknown_page_uses_bilingual_404_handler(client):
    english = client.get("/missing?lang=en")
    arabic = client.get("/missing?lang=ar")

    assert english.status_code == 404
    assert TRANSLATIONS["en"]["error_404"] in english.get_data(as_text=True)
    assert arabic.status_code == 404
    assert TRANSLATIONS["ar"]["error_404"] in arabic.get_data(as_text=True)
    assert 'dir="rtl"' in arabic.get_data(as_text=True)


def test_oversized_request_uses_413_handler(app, pin_verified_client, valid_pdf_upload):
    app.config["MAX_CONTENT_LENGTH"] = 64
    content, filename = valid_pdf_upload

    response = pin_verified_client.post(
        "/upload?lang=en",
        data={"file": (content * 10, filename)},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    assert TRANSLATIONS["en"]["error_413"] in response.get_data(as_text=True)
