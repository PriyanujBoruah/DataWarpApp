---

# Application Release Workflow

This document outlines the complete step-by-step process for releasing a new version of the `DataWarpApp` executable. The workflow is divided into two parts: local preparation and the final GitHub release.

---

## Part 1: Local Development & Build Checklist

**Goal:** To prepare the new version of the application on your local machine.

### ✅ Step 1: Make Code Changes
-   Modify any necessary source files (`app.py`, `*.html`, `*.css`, etc.).
-   Fix bugs, add features, or update text as needed.

### ✅ Step 2: Increment Version Number in `app.py` (CRITICAL)
-   **This is the trigger for the self-update mechanism.**
-   Open `app.py`.
-   Find the `__version__` variable.
-   Increment the version number according to semantic versioning (e.g., from `"1.0.1"` to `"1.0.2"`).

    ```python
    # Example change in app.py
    __version__ = "1.0.2" 
    ```

### ✅ Step 3: Perform a Clean Build
-   Open your terminal (e.g., in VS Code).
-   Activate your virtual environment:
    ```bash
    .\venv\Scripts\activate
    ```
-   **Delete the old build folders** to ensure a fresh build and avoid caching issues:
    ```bash
    # Note: Use 'rmdir /s /q' on Windows Command Prompt or 'rm -rf' on Git Bash/PowerShell
    rmdir /s /q dist
    rmdir /s /q build
    ```
-   Run the PyInstaller build command using the spec file:
    ```bash
    pyinstaller app.spec
    ```
-   A new `dist` folder will be created containing the new `DataWarpApp.exe`.

### ✅ Step 4: Local Verification (Optional but Recommended)
-   Navigate into the newly created `dist` folder.
-   Run `DataWarpApp.exe` to ensure it starts correctly and your latest changes are present.
-   Close the application from the Windows Task Manager when you are finished testing.

### ✅ Step 5: Commit and Tag in Git
-   In your terminal, run the following commands to save your work to Git and prepare for the GitHub release.

1.  **Stage your changes:**
    ```bash
    git add .
    ```

2.  **Commit your changes** (use a meaningful message):
    ```bash
    git commit -m "Update to v1.0.2: Added feature Y and fixed bug Z"
    ```

3.  **Push your code changes to GitHub:**
    ```bash
    git push origin main
    ```

4.  **Create a Git tag** that matches the new version number:
    ```bash
    git tag v1.0.2
    ```

5.  **Push the new tag to GitHub:**
    ```bash
    git push origin v1.0.2
    ```

**Local preparation is complete. Proceed to Part 2.**

---

## Part 2: GitHub Release Checklist

**Goal:** To publish the new executable on GitHub, making it available for the auto-updater.

### ✅ Step 1: Navigate to the Releases Page
-   Go to your repository page on GitHub in your web browser.
-   On the right sidebar, click the **"Releases"** link.

### ✅ Step 2: Draft a New Release
-   Click the **"Draft a new release"** button.

### ✅ Step 3: Select the Tag
-   From the **"Choose a tag"** dropdown menu, select the new tag you just pushed (e.g., `v1.0.2`).
-   The release title will automatically populate with the tag name. You can edit it if you wish.

### ✅ Step 4: Add Release Notes
-   In the description box, write a brief, user-friendly summary of the changes in this version. This helps users know what's new.

    ```markdown
    ### Changes in this version:
    - Fixed a crash that occurred when uploading very large files.
    - The "Download as XLSX" button now works correctly.
    - Added a new "Change Case" feature to the cleaning tools.
    ```

### ✅ Step 5: Attach the Executable Binary (CRITICAL)
-   **This is the most important step for the self-updater to work.**
-   At the bottom of the page, find the box that says **"Attach binaries by dropping them here or selecting them"**.
-   Drag and drop (or select) the new `DataWarpApp.exe` file from your local `dist` folder.
-   **Wait for the upload to complete.**
-   The filename you upload **must** be exactly `DataWarpApp.exe` to match what the update script expects.

### ✅ Step 6: Publish the Release
-   Review all the details one last time.
-   Click the **"Publish release"** button.

**Done!** The new version is now live. Any user running an older version will be notified of the update and can trigger the self-update process through the application.