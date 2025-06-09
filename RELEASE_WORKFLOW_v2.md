# DataWarpApp Final Release Workflow

This document outlines the complete process for creating the initial `v1.0.0` release and then publishing a subsequent update (e.g., `v1.0.1`).

## Part 1: Final Preparation (One-Time Setup)

Ensure these steps are completed before your first release.

### ✅ Step 1: Finalize Project Files

1.  **`app.py`**: Make sure the `__version__` variable is set to your starting version.
    ```python
    __version__ = "1.0.0"
    ```
2.  **`.gitignore`**: Ensure this file exists and is correctly configured to ignore `dist/`, `build/`, `*.spec`, `venv/`, etc.
3.  **`app.spec`**: Confirm this file is configured correctly with all hidden imports and data files (templates, static, .env). It should **not** include `updater.py` or `psutil` if you are using the manual update method.
4.  **`requirements.txt`**: Ensure this file is up-to-date with all necessary packages.
    ```bash
    # (Activate venv)
    pip freeze > requirements.txt
    ```
5.  **Icon File**: Make sure you have an `app_icon.ico` file in your root directory if it's referenced in your `.spec` file.

### ✅ Step 2: Set Up GitHub Repository

1.  If you haven't already, create a **private** repository on GitHub.
2.  Push your entire project to the `main` branch. Make sure your local project is connected to the remote repository.

    ```bash
    # From your project's root folder in the terminal
    git init
    git add .
    git commit -m "Finalize project for initial release"
    git branch -M main
    git remote add origin https://github.com/your_username/DataWarpApp.git
    git push -u origin main
    ```

---

## Part 2: Publishing the Initial Release (`v1.0.0`)

**Goal:** To build the `v1.0.0` executable and publish it as your first official release on GitHub.

### ✅ Step 1: Perform a Clean Build
-   Open your terminal and activate your virtual environment: `.\venv\Scripts\activate`.
-   **Delete** any old `dist` and `build` folders to ensure a fresh build.
-   Run the PyInstaller command:
    ```bash
    pyinstaller app.spec
    ```
-   This will create `/dist/DataWarpApp.exe`, which is your `v1.0.0` application.

### ✅ Step 2: Create the `v1.0.0` Git Tag
-   A tag is a permanent bookmark for this specific version in your code's history.
    ```bash
    # Create a tag that matches the __version__ in app.py
    git tag v1.0.0

    # Push the new tag to GitHub
    git push origin v1.0.0
    ```

### ✅ Step 3: Publish the Release on GitHub
1.  Go to your repository page on GitHub.
2.  Click the **"Releases"** link on the right sidebar.
3.  Click **"Draft a new release"**.
4.  From the **"Choose a tag"** dropdown, select `v1.0.0`.
5.  Set the release title to `Version 1.0.0 - Initial Release`.
6.  In the description, write some notes about the initial release.
7.  **Attach the Executable:** At the bottom, drag and drop the `DataWarpApp.exe` file from your local `dist` folder.
8.  Click **"Publish release"**.

**Congratulations! Your application is now officially released.**

---

## Part 3: Publishing an Update (e.g., `v1.0.1`)

**Goal:** To release a new version that existing users can be notified about.

### ✅ Step 1: Make Code Changes
-   Modify any source files (`app.py`, `templates/index.html`, etc.) as needed for the new version.

### ✅ Step 2: Increment the Version Number in `app.py`
-   Open `app.py`.
-   Change the version variable:
    ```python
    # Example change in app.py
    __version__ = "1.0.1" 
    ```

### ✅ Step 3: Re-build the Executable
-   Follow the same "Clean Build" process as in Part 2, Step 1. This will create a new `DataWarpApp.exe` in your `/dist` folder that contains the `v1.0.1` code.

### ✅ Step 4: Commit and Push Code Changes
-   Save your work to your repository's history.
    ```bash
    git add .
    git commit -m "Update to v1.0.1: Added new feature X"
    git push origin main
    ```

### ✅ Step 5: Create and Push the New Git Tag
-   Create a new tag for the new version.
    ```bash
    git tag v1.0.1
    git push origin v1.0.1
    ```

### ✅ Step 6: Publish the New Release on GitHub
1.  Go back to the **"Releases"** page on GitHub.
2.  Click **"Draft a new release"**.
3.  Choose the new tag (`v1.0.1`).
4.  Add a title and release notes describing the changes.
5.  **Attach the new `v1.0.1` executable** from your local `dist` folder.
6.  Click **"Publish release"**.

### How the Update Works for the User
1.  A user running `v1.0.0` of your app starts it.
2.  The app's background `check_for_updates` function contacts GitHub and sees that the latest release is now `v1.0.1`.
3.  Since `1.0.1` is greater than `1.0.0`, the in-app notification appears.
4.  The user clicks the "Update Now" button.
5.  Their web browser opens to `https://www.datawarp.digital/`.
6.  The user manually downloads the new `DataWarpApp.exe` from your site and replaces their old file.