# tnd-dynhost-ovh

`tnd-dynhost-ovh` is a simple Dockerized Python service that automatically updates the IP address of an OVH DynHost record. It periodically checks the public IP of the host and updates the DynHost entry via OVH’s API if the IP has changed, or after a configurable interval even if the IP remains the same.

## Features

- Periodically checks the public IP address.
- Updates OVH DynHost only when the IP changes, or after a forced interval (`FORCE_UPDATE_HOURS`).
- Stores state in a JSON file named after the host for easy inspection and multi-container support.
- Configurable via environment variables.
- Designed to run as a Docker container.

## Usage

### 1. Clone the repository

```sh
git clone https://github.com/andreatondelli/tnd-dynhost-ovh
cd tnd-dynhost-ovh
```

### 2. Setup

1. Copy the example environment file:

   ```sh
   cp .env.example .env
   ```

2. Edit `.env` and fill in your OVH DynHost credentials and settings.

   **Note:**  
   If your password contains the `$` character, you must double it for Docker Compose.  
   For example, `P4$$w0rd!` should be written as `P4$$$$w0rd!` in your `.env` file.

### 3. Build and run with Docker Compose

```sh
docker-compose up --build
```

The service will start and periodically update your OVH DynHost record.

### 4. Data Persistence

The container stores its state in the `data/` directory as `<OVH_HOST>.json`.  
This allows you to inspect the last known IP and update timestamp for each host, which is especially useful when running multiple containers.

## Environment Variables

- `OVH_HOST`: The DynHost domain to update (e.g., `dynhost.andreatondelli.it`)
- `OVH_USER`: OVH DynHost username
- `OVH_PASS`: OVH DynHost password (remember to double `$` characters)
- `CHECK_INTERVAL_SECONDS`: Seconds between IP checks (default: 60)
- `MIN_SECONDS_BETWEEN_UPDATES`: Minimum seconds between updates if IP unchanged (default: 120)
- `FORCE_UPDATE_HOURS`: Force update even if IP unchanged after this many hours (default: 24)
- `MAX_RETRIES_PER_UPDATE`: Number of retries per update attempt (default: 1)

## Example

To run multiple DynHost updaters, duplicate the service section in [`docker-compose.yaml`](docker-compose.yaml) and set different environment variables and state files.

## License

This project is licensed under the terms of the GNU GPLv3.  
See the [LICENSE](LICENSE) file for details.