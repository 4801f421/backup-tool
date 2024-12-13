import os
import subprocess
import yaml
import tarfile
import requests
from datetime import datetime
import schedule
import time

def load_config():
    """Loads configuration from config.yaml."""
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def run_command(command):
    """
    Runs a shell command and handles errors.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[SUCCESS] Command '{command}' executed successfully.")
        return result.stdout.decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command '{command}' failed with error: {e.stderr.decode('utf-8')}")
    except FileNotFoundError:
        print(f"[ERROR] Command '{command}' not found. Make sure you have the required package manager installed.")

def install_mysqldump():
    print("\nInstalling mysqldump...")
    run_command("sudo apt-get update && sudo apt-get install -y mysql-client")

def install_pg_dump():
    print("\nInstalling pg_dump...")
    run_command("sudo apt-get update && sudo apt-get install -y postgresql-client")

def install_mongodump():
    print("\nInstalling mongodump...")
    commands = [
        "wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -",
        "echo \"deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse\" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list",
        "sudo apt-get update",
        "sudo apt-get install -y mongodb-org-tools"
    ]
    for cmd in commands:
        run_command(cmd)

def install_sqlcmd():
    print("\nInstalling sqlcmd...")
    commands = [
        "curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -",
        "curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list",
        "sudo apt-get update",
        "sudo ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev",
        "echo 'export PATH=$PATH:/opt/mssql-tools/bin' >> ~/.bashrc",
        "source ~/.bashrc"
    ]
    for cmd in commands:
        run_command(cmd)

def install_prerequisites():
    print("Starting the installation of database tools...\n")

    install_mysqldump()
    install_pg_dump()
    install_mongodump()
    install_sqlcmd()

    print("\nInstallation process completed.")

def backup_database(config, output_folder):
    """
    Creates a backup of a specified database based on the configuration and saves it in a specified folder.

    Args:
        config (dict): Configuration dictionary containing database details.
        output_folder (str): Path to the folder where the backup will be saved.

    Returns:
        str: Path to the compressed backup file.

    Raises:
        ValueError: If an unsupported database type is provided.
    """
    name = config["name"]
    db_type = config["db_type"].lower()
    database_name = config["database_name"]
    host = config.get("host", "localhost")
    port = config.get("port", "")
    username = config.get("username", "")
    password = config.get("password", "")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Temporary backup file within the folder
    backup_file = os.path.join(output_folder, f"{name}_{timestamp}")

    # Determine the appropriate backup command based on database type
    if db_type == "mysql" or db_type == "mariadb":
        backup_file += ".sql"
        command = f"mysqldump -h {host} -P {port} -u {username} --password={password} {database_name} > {backup_file}"

    elif db_type == "postgres":
        backup_file += ".sql"
        command = "pg_dump -h {host} -p {port} -U {username} -W {password} {datatabase_name} > {backup_file}"

    elif db_type == "mongodb":
        backup_file += ".gz"
        command = "mongodump --host={host} --port={port} --username={username} --password={password} --archive={backup_file} --gzip"

    elif db_type == "sqlite":
        if not config.get("path"):
            raise ValueError("For SQLite, 'path' must be provided in the config.")
        backup_file += ".sqlite"
        command = ["cp", config["path"], backup_file]

    elif db_type == "mssql":
        backup_file += ".bak"
        command = [
            "sqlcmd",
            f"-S {host}",
            f"-U {username}",
            f"-P {password}",
            "-Q",
            f"BACKUP DATABASE [{database_name}] TO DISK=N'{backup_file}'"
        ]

    else:
        raise ValueError("Unsupported database type. please request databases issue page")

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[SUCCESS] Database backup created: {backup_file}")

        # Create a compressed file in the output folder
        compressed_file = os.path.join(output_folder, f"{database_name}_{timestamp}.tar.gz")
        with tarfile.open(compressed_file, "w:gz") as tar:
            tar.add(backup_file, arcname=os.path.basename(backup_file))

        # Remove the uncompressed backup file
        os.remove(backup_file)

        return compressed_file

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8")
        print(f"[ERROR] Failed to backup database '{database_name}': {error_message}")
        raise RuntimeError(f"Backup failed for database '{database_name}': {error_message}")

    except FileNotFoundError:
        print(f"[ERROR] Command not found for database type '{db_type}'. Make sure the required tool is installed.")
        raise RuntimeError(f"Required tool for '{db_type}' backup is not installed.")

def backup_folder(config, output_folder):
    path = config["path"]
    if not config.get("path") or not config.get("name"):
        raise ValueError("Please provide a path and a name for the backup folder.")
    backup_file = os.path.join(output_folder, f"{config['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz")


    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(path, arcname=os.path.basename(path))

    return backup_file

def backup_docker_volume(config, output_folder):
    name = config["name"]
    if not config.get("name"):
        raise ValueError("Please provide a name for the backup.")
    volume_name = config["volume_name"]
    backup_file = os.path.join(output_folder, f"{config['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz")

    # Check if Docker is installed
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError("Docker is not installed or not available in PATH.")

    # Find the path of the Docker volume
    try:
        volume_inspect = subprocess.run(
            ["docker", "volume", "inspect", volume_name],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        volume_data = eval(volume_inspect.stdout)
        volume_path = volume_data[0]['Mountpoint']
    except subprocess.CalledProcessError:
        raise RuntimeError(f"Docker volume '{volume_name}' not found.")

    # Ensure backup directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Compress the volume path to the backup file
    try:
        subprocess.run(
            ["tar", "-czf", backup_file, "-C", volume_path, "."],
            check=True
        )
        print(f"Backup successful: {backup_file}")
    except subprocess.CalledProcessError:
        raise RuntimeError("Failed to compress the volume directory.")

    return backup_file

def split_large_file(file_path, max_size_mb=40):
    """
    Splits a large file into smaller parts.

    Args:
        file_path (str): Path to the file to split.
        max_size_mb (int): Maximum size of each part in megabytes.

    Returns:
        list: List of paths to the split file parts.
    """
    parts = []
    with open(file_path, "rb") as f:
        part_num = 0
        while chunk := f.read(max_size_mb * 1024 * 1024):
            part_file = f"{file_path}.part{part_num}"
            with open(part_file, "wb") as part:
                part.write(chunk)
            parts.append(part_file)
            part_num += 1
    return parts

def send_to_telegram(token, chat_id, file_path, description):
    """
    Sends a file (or split parts of it) to Telegram.

    Args:
        token (str): Telegram bot token.
        chat_id (str): Telegram chat ID.
        file_path (str): Path to the file to send.
        description (str): Description to attach to the file.
    """
    url = f"https://api.telegram.org/bot{token}/sendDocument"

    # Split the file if it's larger than 1 GB, else use as-is
    parts = split_large_file(file_path) if os.path.getsize(file_path) > 1024 * 1024 * 1024 else [file_path]

    for part in parts:
        with open(part, "rb") as f:
            response = requests.post(url, data={"chat_id": chat_id, "caption": description}, files={"document": f})
        if response.status_code == 200:
            print(f"Part {part} sent successfully to Telegram.")
        else:
            print(f"Failed to send part {part} to Telegram: {response.text}")

def handle_error(token, chat_id, error_message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, data={"chat_id": chat_id, "text": f"Error: {error_message}"})
    if response.status_code != 200:
        print("Failed to send error message to Telegram.")

def schedule_backup(target, config, output_folder):
    """
    Schedules the backup based on the target's schedule.
    """
    schedule_type = target.get("schedule", "daily").lower()
    name = target.get("name", "backup")

    def run_backup():
        print(f"Running backup for {name} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        try:
            if target["type"] == "database":
                backup_file = backup_database(target, output_folder)
            elif target["type"] == "folder":
                backup_file = backup_folder(target, output_folder)
            elif target["type"] == "docker_volume":
                backup_file = backup_docker_volume(target, output_folder)
            else:
                print(f"[ERROR] Unknown target type: {target['type']}")
                return

            # Send backup to Telegram
            description = f"Backup of {target['type']} named {target['name']} taken on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
            send_to_telegram(config["telegram"]["bot_token"], config["telegram"]["chat_id"], backup_file, description)

            # Cleanup backup files
            for part in split_large_file(backup_file):
                os.remove(part)

        except Exception as e:
            print(f"[ERROR] Failed to run backup for {name}: {str(e)}")
            handle_error(config["telegram"]["bot_token"], config["telegram"]["chat_id"], str(e))

    # Map schedule type to appropriate schedule function
    if schedule_type == "hourly":
        schedule.every().hour.do(run_backup)
    elif schedule_type == "daily":
        schedule.every().day.at("00:00").do(run_backup)  # Default to midnight
    elif schedule_type == "weekly":
        schedule.every().week.do(run_backup)
    elif schedule_type == "monthly":
        schedule.every(30).days.do(run_backup)
    else:
        print(f"[WARNING] Unknown schedule type '{schedule_type}' for target {name}. Skipping.")

def main():
    try:
        # Load config
        config = load_config()
        output_folder = config.get("output_folder", "./backups")
        os.makedirs(output_folder, exist_ok=True)

        # Install prerequisites
        install_prerequisites()

        # Schedule backups for each target
        for target in config["backup_targets"]:
            schedule_backup(target, config, output_folder)

        print("[INFO] All backups scheduled. Starting scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(5)

    except Exception as e:
        print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    main()
