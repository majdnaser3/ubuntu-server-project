
import asyncio
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

import flet as ft
import queue


SERVER_KEY = "com.majdnaser3.ubuntu_server_client.server_url"


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError(
            "Enter a valid URL, e.g. http://192.168.1.100:8000"
        )

    return value


def request_json(
    url: str,
    path: str,
    payload=None,
    token=None,
    method=None,):
    headers = {"Accept": "application/json"}

    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{url}{path}",
        data=data,
        headers=headers,
        method=method or ("POST" if payload is not None else "GET"),
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("detail", f"HTTP {exc.code}")
        except (ValueError, AttributeError):
            detail = f"HTTP {exc.code}"

        raise RuntimeError(str(detail)) from exc

    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Cannot reach the server. Check your network and address."
        ) from exc


def check_server(url: str):
    return request_json(url, "/health")



def upload_file_request(
    url: str,
    file_path: str | None,
    token: str,
    file_bytes: bytes | None = None,
    filename: str | None = None,
):
    import mimetypes
    import os
    import uuid

    filename = filename or os.path.basename(file_path or "upload")

    content_type = (
        mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    if file_bytes is None:
        if not file_path:
            raise RuntimeError("Could not access the selected file.")
        with open(file_path, "rb") as f:
            file_bytes = f.read()

    boundary = uuid.uuid4().hex

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="uploaded_file"; '
        f'filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        f"{url}/files/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = response.read().decode("utf-8")
            return json.loads(result) if result else {}

    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get(
                "detail", f"HTTP {exc.code}"
            )
        except (ValueError, AttributeError):
            detail = f"HTTP {exc.code}"
        raise RuntimeError(str(detail)) from exc

    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach the server.") from exc




def download_file_to_bytes(
    url: str,
    file_id: int,
    token: str,
    progress_queue,
):
    request = urllib.request.Request(
        f"{url}/files/{file_id}/download",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            file_data = bytearray()

            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break

                file_data.extend(chunk)
                downloaded += len(chunk)
                progress_queue.put((downloaded, total_size))

            return bytes(file_data)

    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(
                exc.read().decode("utf-8")
            ).get("detail", f"HTTP {exc.code}")
        except (ValueError, AttributeError):
            detail = f"HTTP {exc.code}"

        raise RuntimeError(str(detail)) from exc

    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach the server.") from exc


async def main(page: ft.Page):
    page.title = "Ubuntu Server Client"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 20

    prefs = ft.SharedPreferences()
    server_url = None
    access_token = None
    current_username = None

    async def connect(url: str, save: bool = True):
        nonlocal server_url

        try:
            url = normalize_url(url)
            await asyncio.to_thread(check_server, url)

            if save:
                await prefs.set(SERVER_KEY, url)

            server_url = url
            show_auth()

        except ValueError as exc:
            show_setup(url, str(exc))

        except Exception as exc:
            show_setup(url, str(exc))

    def show_setup(initial_url="", message=""):
        page.appbar = None
        page.clean()

        address = ft.TextField(
            label="Server address",
            hint_text="http://192.168.1.100:8000",
            value=initial_url,
            autofocus=True,
            width=360,
        )

        status = ft.Text(
            message,
            color=ft.Colors.RED if message else ft.Colors.ON_SURFACE,
            text_align=ft.TextAlign.CENTER,
        )

        async def connect_clicked(e):
            status.value = "Connecting..."
            status.color = ft.Colors.BLUE
            page.update()
            await connect(address.value or "")

        async def cancel_clicked(e):
            saved = await prefs.get(SERVER_KEY)
            if saved:
                await connect(saved, save=False)

        controls = [
            ft.Icon(ft.Icons.DNS, size=52),
            ft.Text(
                "Connect to your server",
                size=24,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Enter your Ubuntu server address. "
                "You only need to configure it once.",
                text_align=ft.TextAlign.CENTER,
            ),
            address,
            status,
            ft.Button(
                "Save and connect",
                icon=ft.Icons.LINK,
                on_click=connect_clicked,
                width=240,
            ),
        ]

        if server_url:
            controls.append(
                ft.TextButton("Cancel", on_click=cancel_clicked)
            )

        page.add(
            ft.Container(
                content=ft.Column(
                    controls,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=18,
                    scroll=ft.ScrollMode.AUTO,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        )
        page.update()

    def show_auth(message="", username="", register=False):
        page.appbar = None
        page.clean()

        username_field = ft.TextField(
            label="Username",
            value=username,
            autofocus=True,
            width=320,
            max_length=50,
        )
        password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=320,
            max_length=128,
        )
        status = ft.Text(
            message,
            color=ft.Colors.RED if message else ft.Colors.ON_SURFACE,
            text_align=ft.TextAlign.CENTER,
        )

        async def submit(e):
            nonlocal access_token, current_username

            name = (username_field.value or "").strip()
            password = password_field.value or ""

            if not name or not password:
                status.value = "Enter your username and password."
                status.color = ft.Colors.RED
                page.update()
                return

            if register and len(name) < 3:
                status.value = "Username must contain at least 3 characters."
                status.color = ft.Colors.RED
                page.update()
                return

            if register and len(password) < 8:
                status.value = "Password must contain at least 8 characters."
                status.color = ft.Colors.RED
                page.update()
                return

            status.value = "Please wait..."
            status.color = ft.Colors.BLUE
            page.update()

            try:
                payload = {"username": name, "password": password}

                result = await asyncio.to_thread(
                    request_json,
                    server_url,
                    "/register" if register else "/login",
                    payload,
                )

                if register:
                    show_auth(
                        message="Account created. You can now log in.",
                        username=name,
                    )
                else:
                    access_token = result["access_token"]
                    current_username = name
                    await show_home()

            except Exception as exc:
                status.value = str(exc)
                status.color = ft.Colors.RED
                page.update()

        async def switch_mode(e):
            show_auth(
                username=username_field.value or "",
                register=not register,
            )

        async def change_server(e):
            show_setup(server_url)

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=56),
                        ft.Text(
                            "Create an account" if register else "Welcome back",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            server_url or "",
                            size=12,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        username_field,
                        password_field,
                        status,
                        ft.Button(
                            "Create account" if register else "Log in",
                            on_click=submit,
                            width=240,
                        ),
                        ft.TextButton(
                            (
                                "Already have an account? Log in"
                                if register
                                else "New here? Create an account"
                            ),
                            on_click=switch_mode,
                        ),
                        ft.TextButton(
                            "Change server address",
                            on_click=change_server,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=14,
                    scroll=ft.ScrollMode.AUTO,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        )
        page.update()

    
    async def show_home():
        page.clean()

        files_view = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        
        async def download_selected_file(item):
            file_id = item.get("id")
            filename = item.get("original_filename", "download")

            if file_id is None:
                snackbar = ft.SnackBar(
                    content=ft.Text("Could not identify this file.")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()
                return

            try:
                progress_queue = queue.Queue()
                progress_bar = ft.ProgressBar(value=0)
                progress_text = ft.Text("Preparing download...")

                page.overlay.extend([progress_bar, progress_text])
                page.update()

                downloaded = 0
                total_size = 0

                download_task = asyncio.create_task(
                    asyncio.to_thread(
                        download_file_to_bytes,
                        server_url,
                        file_id,
                        access_token,
                        progress_queue,
                    )
                )

                while not download_task.done() or not progress_queue.empty():
                    try:
                        while True:
                            downloaded, total_size = progress_queue.get_nowait()
                    except queue.Empty:
                        pass

                    if total_size > 0:
                        progress_bar.value = downloaded / total_size
                        progress_text.value = (
                            f"Downloading: {downloaded / total_size * 100:.0f}% "
                            f"({downloaded / 1024**2:.1f} / "
                            f"{total_size / 1024**2:.1f} MB)"
                        )
                    else:
                        progress_text.value = (
                            f"Downloaded {downloaded / 1024**2:.1f} MB"
                        )

                    page.update()
                    await asyncio.sleep(0.1)

                file_bytes = await download_task

                page.overlay.remove(progress_bar)
                page.overlay.remove(progress_text)
                page.update()

                destination = await file_picker.save_file(
                    file_name=filename,
                    src_bytes=file_bytes,
                )

                if destination is None:
                    return

                snackbar = ft.SnackBar(
                    content=ft.Text(f"File saved: {filename}")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()


            except Exception as exc:
                if 'progress_bar' in locals() and progress_bar in page.overlay:
                    page.overlay.remove(progress_bar)

                if 'progress_text' in locals() and progress_text in page.overlay:
                    page.overlay.remove(progress_text)

                page.update()
                snackbar = ft.SnackBar(
                    content=ft.Text(f"Download failed: {exc}")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()
        async def confirm_delete_file(item):
            file_id = item.get("id")
            filename = item.get("original_filename", "this file")

            if file_id is None:
                return

            async def delete_file(e):
                dialog.open = False
                page.update()

                try:
                    await asyncio.to_thread(
                        request_json,
                        server_url,
                        f"/files/{file_id}",
                        None,
                        access_token,
                        "DELETE",
                    )

                    await load_files()

                    snackbar = ft.SnackBar(
                        content=ft.Text(f"Deleted: {filename}")
                    )
                except Exception as exc:
                    snackbar = ft.SnackBar(
                        content=ft.Text(f"Delete failed: {exc}")
                    )

                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete file?"),
                content=ft.Text(
                    f'Are you sure you want to permanently delete "{filename}"?'
                ),
                actions=[
                    ft.TextButton(
                        "Cancel",
                        on_click=lambda e: close_dialog(),
                    ),
                    ft.TextButton(
                        "Delete",
                        on_click=delete_file,
                    ),
                ],
            )

            def close_dialog():
                dialog.open = False
                page.update()

            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        async def load_files(e=None):
            files_view.controls = [
                ft.ProgressRing(),
                ft.Text("Loading your files..."),
            ]
            page.update()

            try:
                files = await asyncio.to_thread(
                    request_json,
                    server_url,
                    "/files",
                    None,
                    access_token,
                )

                files_view.controls.clear()

                if not files:
                    files_view.controls.append(
                        ft.Text("No files yet. Your storage is empty.")
                    )
                else:
                    for item in files:
                        size = item.get("size_bytes", 0)
                        if size < 1024:
                            size_text = f"{size} B"
                        elif size < 1024**2:
                            size_text = f"{size / 1024:.1f} KB"
                        elif size < 1024**3:
                            size_text = f"{size / 1024**2:.1f} MB"
                        else:
                            size_text = f"{size / 1024**3:.2f} GB"

                        files_view.controls.append(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.INSERT_DRIVE_FILE,
                                            size=28,
                                        ),
                                                                                
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    item.get(
                                                        "original_filename",
                                                        "Unnamed file",
                                                    ),
                                                    weight=ft.FontWeight.BOLD,
                                                    max_lines=2,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    expand=True,
                                                ),
                                                ft.Text(
                                                    f"{size_text}  •  "
                                                    f"{item.get('created_at', '')}",
                                                    size=12,
                                                ),
                                            ],
                                            spacing=4,
                                            expand=True,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DOWNLOAD,
                                            tooltip="Download file",
                                            on_click=lambda e, file_item=item: asyncio.create_task(
                                                download_selected_file(file_item)
                                            ),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            tooltip="Delete file",
                                            icon_color=ft.Colors.RED,
                                            on_click=lambda e, file_item=item: asyncio.create_task(
                                                confirm_delete_file(file_item)
                                            ),
                                        ),

                                    ],
                                    spacing=12,
                                ),
                                padding=12,
                                border=ft.Border.all(
                                    1, ft.Colors.OUTLINE_VARIANT
                                ),
                                border_radius=10,
                            )
                        )

            except Exception as exc:
                files_view.controls = [
                    ft.Text(
                        f"Could not load files: {exc}",
                        color=ft.Colors.RED,
                    ),
                    ft.Button("Try again", on_click=load_files),
                ]

            page.update()

        page.appbar = ft.AppBar(
            title=ft.Text("My Files"),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Refresh files",
                    on_click=load_files,
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Server settings",
                    on_click=lambda e: show_setup(server_url),
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Log out",
                    on_click=lambda e: logout(),
                ),
            ],
        )

        
        async def upload_selected_file(e=None):
            selected = await file_picker.pick_files(
                allow_multiple=False,
                with_data=True,
            )

            if not selected:
                return

            file = selected[0]
            file_path = file.path
            file_bytes = file.bytes

            if file_bytes is None and not file_path:
                snackbar = ft.SnackBar(
                    content=ft.Text("Could not access the selected file.")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()
                return

            snackbar = ft.SnackBar(
                content=ft.Text("Uploading file...")
            )
            page.overlay.append(snackbar)
            snackbar.open = True
            page.update()

            try:
                await asyncio.to_thread(
                    upload_file_request,
                    server_url,
                    file_path,
                    access_token,
                    file_bytes,
                    file.name,
                )

                snackbar = ft.SnackBar(
                    content=ft.Text("File uploaded successfully!")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()
                await load_files()

            except Exception as exc:
                snackbar = ft.SnackBar(
                    content=ft.Text(f"Upload failed: {exc}")
                )
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()

        file_picker = ft.FilePicker()
        page.services.append(file_picker)


        page.add(
            ft.Column(
                [
                    ft.Text(
                        f"Welcome, {current_username}!",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text("Files stored on your Ubuntu server"),
                    ft.Divider(),
                    ft.Button(
                    "Upload file",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=upload_selected_file,
                    ),
                    files_view,
                ],
                expand=True,
                spacing=12,
            )
        )

        page.update()
        await load_files()

        page.update()

    def logout():
        nonlocal access_token, current_username
        access_token = None
        current_username = None
        show_auth()

    saved_url = await prefs.get(SERVER_KEY)

    if saved_url:
        await connect(saved_url, save=False)
    else:
        show_setup()


if __name__ == "__main__":
    ft.run(main)
