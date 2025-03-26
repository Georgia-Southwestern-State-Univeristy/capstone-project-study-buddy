# Flask Backend Application

This is the backend of the project built using **Python** and **Flask**, a lightweight web framework for building web applications. This document provides instructions on how to set up and run the Flask server, including dependencies and configurations.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- Python 3.8+
- Virtualenv (optional but recommended)
- Git (for cloning the repository)
- A package manager like `pip`

## Project Setup

1. **Clone the repository**:
   ```
   git clone https://github.com/Georgia-Southwestern-State-Univeristy/capstone-project-study-buddy.git
   cd server
   ```

2. **Create and activate a virtual environment (optional but recommended)**:
    ```
    python -m venv venv
    source venv/bin/activate  # On Windows use: .\venv\Scripts\Activate.ps1
    ```

3. **Configure environment variables**:
   - Copy the `.env.example` file to a new file named `.env`.
   - Update the `.env` file with your specific configurations.
   ```
   cp .env.example .env
   ```
4.  **Install the required dependencies**:
    ```
    pip install -r requirements.txt
    ```

5. **Run app.py**
   ```
   python app.py
   ```

---
## Install FFmpeg and Add FFmpeg to System PATH

### Download and Extract FFmpeg Properly

1. **Download FFmpeg Again:**
   - Go to the [FFmpeg download page](https://ffmpeg.org/download.html).
   - Click on the link for Windows builds provided by Gyan or BtbN (these are popular and reliable sources). This will redirect you to their respective pages where you can download the build.
   - Choose a static build (which includes all necessary files in a single package) and download the zip file.

2. **Extract the FFmpeg Zip File:**
   - Once downloaded, right-click on the zip file and choose 'Extract All...' or use any preferred extraction tool like 7-Zip or WinRAR.
   - Choose a location where you want to extract the files. You can extract them directly to `C:\FFmpeg` to keep things organized.

3. **Verify the Contents:**
   - Navigate to the folder where you extracted the files.
   - You should see a `bin` folder inside this directory. Inside `bin`, there will be at least three files: `ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`.

### Add FFmpeg to System PATH

If you've successfully located the `bin` folder now:

1. **Edit the PATH Environment Variable:**
   - Press `Windows key + R`, type `sysdm.cpl`, and press Enter.
   - Go to the 'Advanced' tab and click on 'Environment Variables'.
   - Under 'System Variables', scroll down to find the 'Path' variable and click on 'Edit'.
   - Click 'New' and add the full path to the `bin` folder, e.g., `C:\FFmpeg\bin`.
   - Click 'OK' to save your changes and close all remaining windows by clicking 'OK'.

2. **Verify FFmpeg Installation:**
   - Open a new command prompt or PowerShell window (make sure to open it after updating the PATH).
   - Type `ffmpeg -version` and press Enter. This command should now return the version of FFmpeg, confirming it's installed correctly and recognized by the system.


---
# Deploying the Flask Backend to Azure

This guide will help you create an Azure Container Registry (ACR), build your Docker image, push it to your registry, and deploy your Flask application using Azure Container Apps.

## Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`).
- Docker Desktop installed with [Buildx enabled](https://docs.docker.com/build/buildx/).
- A working Flask application (with a proper `Dockerfile`).

## 1. Create an Azure Container Registry (ACR)

Create a resource group (if you don’t have one):

```bash
az group create --name MyResourceGroup --location eastus
```

Create the container registry:

```bash
az acr create --resource-group MyResourceGroup \
  --name <your-registry-name> \
  --sku Basic \
  --admin-enabled true
```

> Replace `<your-registry-name>` with a unique name (e.g., `myappregistry`).

## 2. Log In to Your Container Registry

Log in to your registry so that Docker can push images to it:

```bash
az acr login --name <your-registry-name>
```

## 3. Build and Push Your Docker Image

Make sure you’re in the root folder of your project (where the `Dockerfile` is located) and run:

```bash
docker buildx build --platform linux/amd64 \
  -t <your-registry-name>.azurecr.io/meme-mingle:latest \
  --push .
```

This command uses Buildx to build the image for the `linux/amd64` platform, tags it appropriately, and pushes it directly to your ACR.

> **Tip:** If you need to support multiple platforms (e.g., linux/arm64), add them to the `--platform` flag as a comma-separated list.

## 4. Create an Azure Container App

Now that your image is in ACR, deploy it as a container app. First, create a Container Apps environment:

```bash
az containerapp env create --resource-group MyResourceGroup \
  --name MyContainerAppEnv --location eastus
```

Then, create the container app:

```bash
az containerapp create --resource-group MyResourceGroup \
  --name my-flask-app \
  --environment MyContainerAppEnv \
  --image <your-registry-name>.azurecr.io/meme-mingle:latest \
  --target-port 80 \
  --ingress 'external'
```

> This command creates a container app named `my-flask-app` that exposes port 80 publicly. Adjust the target port and ingress settings if needed.

## 5. Verify Your Deployment

After the deployment is complete, get the container app’s URL:

```bash
az containerapp show --name my-flask-app --resource-group MyResourceGroup --query properties.configuration.ingress.fqdn -o tsv
```

Visit the URL in your browser to confirm that your Flask application is running.

---

By following these steps, you have successfully:

1. Created an Azure Container Registry.
2. Logged into ACR.
3. Built and pushed your Docker image using Buildx.
4. Deployed your Flask backend as an Azure Container App.

For more details on each command, refer to the [Azure CLI documentation](https://docs.microsoft.com/en-us/cli/azure/).

