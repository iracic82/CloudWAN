import os
import boto3
from boto3.dynamodb.conditions import Key

# ─── CONFIG ───────────────────────────────────────────
VPC_RT_ID        = "rtb-0f6f475814a6c7ca6"
CIDR_BLOCK       = "192.168.0.0/16"
CORE_NETWORK_ID  = "core-network-0cd5a772baedb9e3f"
SNS_TOPIC_ARN    = "arn:aws:sns:eu-west-1:905418046272:route-monitor-alerts"
DDB_TABLE_NAME   = "CloudWANPeerState"
# ──────────────────────────────────────────────────────

ec2 = boto3.client("ec2")
ddb = boto3.resource("dynamodb").Table(DDB_TABLE_NAME)
sns = boto3.client("sns")

def lambda_handler(event, context):
    detail      = event.get("detail", {})
    change_type = detail.get("changeType")

    # only handle the BGP status‐update events that carry a connectPeerArn
    if change_type not in ("CONNECT_PEER_BGP_UP", "CONNECT_PEER_BGP_DOWN"):
        print(f"ℹ️ skipping non‐BGP event: {change_type}")
        return

    peer_arn = detail.get("connectPeerArn")
    if not peer_arn:
        print("⚠️ no connectPeerArn in detail, skipping")
        return

    # map BGP UP/DOWN to our “UP”/“DOWN” state
    new_state = "UP" if change_type == "CONNECT_PEER_BGP_UP" else "DOWN"

    # 1) read existing peer states
    resp = ddb.scan(
        ProjectionExpression="PeerArn,#S",
        ExpressionAttributeNames={"#S": "State"}
    )
    items = { item["PeerArn"]: item["State"] for item in resp["Items"] }
    old_state = items.get(peer_arn)
    print(f"{peer_arn}: {old_state} → {new_state}")

    # 2) persist only on change
    if old_state != new_state:
        ddb.update_item(
            Key={ "PeerArn": peer_arn },
            UpdateExpression="SET #S = :s",
            ExpressionAttributeNames={"#S": "State"},
            ExpressionAttributeValues={":s": new_state}
        )
        print(f"✅ DynamoDB updated: {peer_arn} = {new_state}")
    else:
        print("ℹ️ no change, skipping Dynamo write")

    # 3) recalc aggregate health across all peers
    items[peer_arn] = new_state
    up_count = sum(1 for s in items.values() if s == "UP")
    print(f"  → peers UP: {up_count}/{len(items)}")

    # 4) if any are UP, ensure route; if none, delete it
    if up_count > 0:
        _ensure_route()
    else:
        _delete_route()

def _ensure_route():
    rts = ec2.describe_route_tables(RouteTableIds=[VPC_RT_ID])["RouteTables"][0]["Routes"]
    if not any(r.get("DestinationCidrBlock") == CIDR_BLOCK for r in rts):
        print(f"➕ adding route {CIDR_BLOCK}")
        ec2.create_route(
            RouteTableId         = VPC_RT_ID,
            DestinationCidrBlock = CIDR_BLOCK,
            CoreNetworkArn       = f"arn:aws:networkmanager::905418046272:core-network/{CORE_NETWORK_ID}"
        )
        sns.publish(
            TopicArn = SNS_TOPIC_ARN,
            Subject  = "✅ Anycast route added",
            Message  = f"Added {CIDR_BLOCK} to RT {VPC_RT_ID}"
        )
    else:
        print("✅ route already exists; skipping")

def _delete_route():
    try:
        print(f"❌ deleting route {CIDR_BLOCK}")
        ec2.delete_route(
            RouteTableId         = VPC_RT_ID,
            DestinationCidrBlock = CIDR_BLOCK
        )
        sns.publish(
            TopicArn = SNS_TOPIC_ARN,
            Subject  = "🛑 Anycast route removed",
            Message  = f"Removed {CIDR_BLOCK} from RT {VPC_RT_ID}"
        )
    except ec2.exceptions.ClientError as e:
        if "InvalidRoute.NotFound" in str(e):
            print("ℹ️ route not present; nothing to delete")
        else:
            print("🔥 delete error:", e)
            sns.publish(
                TopicArn = SNS_TOPIC_ARN,
                Subject  = "❌ Delete-route error",
                Message  = f"Error deleting {CIDR_BLOCK}: {e}"
            )
