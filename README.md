# Docker and Database Backup Tool

This project is a Python-based backup tool designed to support:

- **Docker container volumes**
- **All types of databases**

It uses `schedule` for automated backups and supports various scheduling configurations.

## Features

- **Backup Docker Volumes:** Automatically backs up specified Docker volumes to a target directory.
- **Database Backup:** Supports backups for various databases (e.g., MongoDB, MySQL, PostgresSQL, MSSQL, etc.).
- **Customizable Scheduling:** Easily configure backup intervals (e.g., daily, weekly, hourly).
- **Lightweight and Extensible:** The codebase is simple to modify for additional features.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/4801f421/backup-tool.git
   cd backup-tool
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Configuration
Edit the `config.yaml` file to include your backup settings (e.g., volume paths, database credentials, and backup schedules).
   
   Example:
   ```yaml
output_folder: /path/to/folder/for/saving/backups
telegram:
   bot_token: telegram_bot_token # receive from https://t.me/BotFather
   chat_id: telegram_user_chat_id # receive from https://t.me/userinfobot
backup_targets:
  - type: database
    name: db_of_project1
    db_type: mongodb # mongodb, postgres, mysql, mariadb, sqlite, mssql
    database_name: database_name
    host: localhost
    port: 27017
    username: admin
    password: admin123
    schedule: daily # hourly, daily, weekly, monthly
    path: /path/to/database.db # only required for sqlite
  - type: folder
    name: logs_folder
    path: /path/to/folder
  - type: docker_volume
    name: backup_name
    volume_name: volume_name # find using `docker volume ls`
   ```

### Running the Script

Run the script using:
```bash
python3 main.py
```

---

## Scheduling

This tool uses the `schedule` library to manage backups. By default, it checks every 5 second if a task is due. Adjust the timing in `main.py` if necessary.

---

## Contributing

Contributions are welcome! Feel free to fork this repository, make changes, and submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more information.

---

## Contact

For questions or feedback, contact me at:
- Email: 4801f4214lin32had@gmail.com
- GitHub: [4801f421](https://github.com/4801f421)
