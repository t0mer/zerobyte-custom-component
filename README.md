# Zerobyte Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/release/t0mer/zerobyte-custom-component.svg)](https://github.com/t0mer/zerobyte-custom-component/releases)
[![License](https://img.shields.io/github/license/t0mer/zerobyte-custom-component.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration for [Zerobyte](https://github.com/t0mer/zerobyte) — a self-hosted backup management platform built on [restic](https://restic.net/). Monitor volumes, repositories, and backup schedules directly from Home Assistant, and trigger backup operations through the HA dashboard or automations.

## Zerobyte Application

![Zerobyte Application](https://raw.githubusercontent.com/t0mer/zerobyte-custom-component/main/assets/screenshots/zerobyte_dashboard.png)

Zerobyte provides a web-based UI to manage restic backup repositories, backup volumes, and scheduled jobs. This integration brings all of that data into Home Assistant as sensors, switches, and action buttons.

---

## Features

- **Volume monitoring** — track total, used, and free storage for each backup volume, and see whether it is mounted
- **Repository monitoring** — per-repository status, last health-check timestamp, snapshot count, and latest snapshot time
- **Schedule monitoring** — last backup status and timestamp, next scheduled backup time, and enable/disable toggle
- **Action buttons** — run a backup now, stop a running backup, trigger retention policy (forget), mount or unmount a volume
- **Configurable poll interval** — 1 minute to 24 hours (default: 5 minutes), adjustable at any time from the integration options

---

## Prerequisites

- A running [Zerobyte](https://github.com/t0mer/zerobyte) instance reachable from your Home Assistant host
- Home Assistant 2024.1.0 or newer
- [HACS](https://hacs.xyz/) installed in Home Assistant

---

## Installation via HACS

Because this integration is not in the default HACS store, add it as a **custom repository** first.

### Step 1 — Add the custom repository

1. Open **HACS** in Home Assistant.

   ![HACS Integrations](https://raw.githubusercontent.com/t0mer/zerobyte-custom-component/main/assets/screenshots/hacs_integrations.png)

2. Click the **⋮** (three-dot) menu in the top-right corner and choose **Custom repositories**.

3. In the dialog that opens, paste the repository URL and select **Integration** as the category:

   | Field | Value |
   |---|---|
   | Repository URL | `https://github.com/t0mer/zerobyte-custom-component` |
   | Category | Integration |

4. Click **Add**. The Zerobyte repository will be added to your HACS store.

### Step 2 — Download the integration

Search for **Zerobyte** in the HACS integrations list:

![HACS Search](https://raw.githubusercontent.com/t0mer/zerobyte-custom-component/main/assets/screenshots/hacs_search.png)

Click the **Zerobyte** card, then click **Download** and confirm. Wait for the download to complete.

### Step 3 — Restart Home Assistant

After HACS finishes downloading, restart Home Assistant so the integration is loaded:

**Settings → System → Restart**

---

## Configuration

After restarting, add the integration through the standard HA flow.

### Step 1 — Add the integration

Go to **Settings → Devices & Services** and click **+ Add integration**.

![Add Integration](https://raw.githubusercontent.com/t0mer/zerobyte-custom-component/main/assets/screenshots/add_integration_dialog.png)

Search for **Zerobyte** and click the result.

### Step 2 — Enter your Zerobyte server details

| Field | Description | Example |
|---|---|---|
| **Server URL** | Base URL of your Zerobyte server | `http://192.168.1.10:4096` |
| **Username** | Your Zerobyte account username | `admin` |
| **Password** | Your Zerobyte account password | _(your password)_ |

Click **Submit**. The integration validates the credentials and, if successful, creates a device for every volume, repository, and backup schedule it finds on the server.

### Step 3 — Adjust poll interval (optional)

Open the Zerobyte integration card and click **Configure** to change how often HA polls the server (default: every 5 minutes, range: 1–1440 minutes).

---

## Entities

The integration creates a device per **volume**, per **repository**, and per **backup schedule**. The entities on each device are described below.

### Volume devices

| Entity | Type | Description |
|---|---|---|
| Mounted | Binary sensor | `On` when the volume status is `mounted` |
| Storage Total | Sensor (GiB) | Total capacity of the volume |
| Storage Used | Sensor (GiB) | Used space on the volume |
| Storage Free | Sensor (GiB) | Available free space |
| Mount | Button | Mount the volume |
| Unmount | Button | Unmount the volume |

**Extra attributes on volume entities:** `backend`, `path`, `status`, `last_health_check`, `last_error`

### Repository devices

| Entity | Type | Description |
|---|---|---|
| Status | Sensor | Current repository status (e.g. `ready`) |
| Last Checked | Sensor (timestamp) | Time of the last health check |
| Snapshot Count | Sensor | Total number of snapshots in the repository |
| Latest Snapshot | Sensor (timestamp) | Creation time of the most recent snapshot |

**Extra attributes on repository sensors:** `backend`, `compression_mode`, `created_at`, `path`/`bucket`/`remote`, `last_error`

**Extra attributes on Latest Snapshot:** `snapshot_id`, `hostname`, `paths`, `tags`

### Backup schedule devices

| Entity | Type | Description |
|---|---|---|
| Last Backup Status | Sensor | Result of the last backup run (e.g. `success`, `error`) |
| Last Backup | Sensor (timestamp) | When the last backup completed |
| Next Backup | Sensor (timestamp) | When the next backup is scheduled |
| Enabled | Switch | Enable or disable the schedule |
| Run Backup | Button | Trigger an immediate backup run |
| Stop Backup | Button | Abort a running backup |
| Run Retention | Button | Execute the retention (forget) policy now |

**Extra attributes on schedule entities:** `cron_expression`, `backup_paths`, `exclude_patterns`, `retention_policy`, `volume`, `repository`, `last_backup_error`

---

## Usage examples

### Automation: alert on backup failure

```yaml
automation:
  alias: "Alert on backup failure"
  trigger:
    - platform: state
      entity_id: sensor.my_schedule_last_backup_status
      to: "error"
  action:
    - service: notify.mobile_app_my_phone
      data:
        title: "Backup failed"
        message: "The scheduled backup on Zerobyte has failed."
```

### Automation: run a backup every morning

```yaml
automation:
  alias: "Daily backup at 3 AM"
  trigger:
    - platform: time
      at: "03:00:00"
  action:
    - service: button.press
      target:
        entity_id: button.my_schedule_run_backup
```

### Dashboard card: volume space at a glance

```yaml
type: entities
title: Backup Volume
entities:
  - entity: binary_sensor.my_volume_mounted
  - entity: sensor.my_volume_storage_total
  - entity: sensor.my_volume_storage_used
  - entity: sensor.my_volume_storage_free
```

---

## Troubleshooting

| Symptom | Resolution |
|---|---|
| "Cannot connect" during setup | Verify the Server URL is reachable from the HA host and the port is correct |
| "Invalid auth" during setup | Check username and password against the Zerobyte UI |
| Entities show as unavailable | The Zerobyte server may be down or unreachable; check the HA logs for details |
| No devices created | Zerobyte has no volumes, repositories, or schedules configured yet |

---

## Links

- [Zerobyte application](https://github.com/t0mer/zerobyte)
- [HACS](https://hacs.xyz/)
- [Report an issue](https://github.com/t0mer/zerobyte-custom-component/issues)
