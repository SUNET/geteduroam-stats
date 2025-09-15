#!/usr/bin/env python3

import os
import mariadb

from datetime import datetime
import json

from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)

alloy_host = os.environ["ALLOY_HOST"]
db_host = os.environ["DB_HOST"]
db_name = os.environ["DB_NAME"]
db_pass = os.environ["DB_PASS"]
db_user = os.environ["DB_USER"]
service_name = os.environ["SERVICE_NAME"]

# Service name is required for most backends,
# and although it's not necessary for console export,
# it's good to set service name anyways.
resource = Resource.create(attributes={SERVICE_NAME: service_name})

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=f"http://{alloy_host}:4317")
)
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)
meter = metrics.get_meter(service_name)


connection = mariadb.connect(
    user=db_user, password=db_pass, host=db_host, database=db_name
)

cursor = connection.cursor()

profiles = {}
users = {}
try:
    statement = "SELECT requester,revoked,expires FROM realm_signing_log"
    cursor.execute(statement)
    present = datetime.now()
    for requester, revoked, expires in cursor:
        active = False
        org = requester.split("@")[1]

        if org not in profiles:
            profiles[org] = {"active": 0, "revoked": 0, "expired": 0}

        if revoked:
            profiles[org]["revoked"] += 1
        elif present > expires:
            profiles[org]["expired"] += 1
        else:
            active = True
            profiles[org]["active"] += 1

        if org not in users:
            users[org] = {"active": [], "inactive": []}

        if active:
            if requester not in users[org]["active"]:
                users[org]["active"].append(requester)
            if requester in users[org]["inactive"]:
                users[org]["inactive"].remove(requester)
        else:
            if requester in users[org]["active"]:
                pass
            elif requester not in users[org]["inactive"]:
                users[org]["inactive"].append(requester)

except mariadb.Error as e:
    print(f"Error retrieving entry from database: {e}")

output = {}
for org in profiles:
    output[org] = {
        "profiles": profiles[org],
        "users": {
            "active": len(users[org]["active"]),
            "inactive": len(users[org]["inactive"]),
        },
    }


print(json.dumps(output))
for org in output:
    attributes = {"organisation": org}

    users_active = meter.create_gauge(
        name="users_active",
        description="active_users",
    )
    users_inactive = meter.create_gauge(
        name="users_inactive",
        description="inactive_users",
    )

    profiles_expired = meter.create_gauge(
        name="profiles_expired",
        description="expired_profiles",
    )
    profiles_active = meter.create_gauge(
        name="profiles_active",
        description="active_profiles",
    )
    profiles_revoked = meter.create_gauge(
        name="profiles_revoked",
        description="revoked_profiles",
    )
    users_active.set(output[org]["users"]["active"], attributes)
    users_inactive.set(output[org]["users"]["inactive"], attributes)
    profiles_expired.set(output[org]["profiles"]["expired"], attributes)
    profiles_active.set(output[org]["profiles"]["active"], attributes)
    profiles_revoked.set(output[org]["profiles"]["revoked"], attributes)
