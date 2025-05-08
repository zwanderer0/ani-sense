import streamlit as st
import paho.mqtt.client as mqtt
import time
import ssl

# MQTT Configuration
MQTT_BROKER_HOST = "p02bbe2c.ala.us-east-1.emqxsl.com"
MQTT_BROKER_PORT = 8883
MQTT_TOPIC_SUBSCRIBE = "apollo-air-1-10b368/#"  # Subscribe to all topics under the device
CA_CERT_PATH = "emqxsl-ca.crt"

# --- MQTT Client Setup ---
# Initialize a list in session state to store messages
if 'mqtt_messages' not in st.session_state:
    st.session_state.mqtt_messages = []
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_connected = True
        st.session_state.mqtt_messages.append(("Status", "Connected to MQTT Broker!"))
        client.subscribe(MQTT_TOPIC_SUBSCRIBE)
        st.session_state.mqtt_messages.append(("Status", f"Subscribed to {MQTT_TOPIC_SUBSCRIBE}"))
    else:
        st.session_state.mqtt_connected = False
        st.session_state.mqtt_messages.append(("Error", f"Failed to connect, return code {rc}"))

def on_message(client, userdata, msg):
    # Prepend new messages to the list
    st.session_state.mqtt_messages.insert(0, (msg.topic, msg.payload.decode()))
    # Keep only the last 100 messages to avoid growing too large
    st.session_state.mqtt_messages = st.session_state.mqtt_messages[:100]
    # We need to tell Streamlit to rerun to update the UI
    # This is a bit of a hack for real-time updates in a loop
    # More robust solutions might involve Streamlit's experimental rerun or custom components
    if hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else: # For older streamlit versions
        st.legacy_caching.clear_cache() # May not always work as expected for reruns
        st.experimental_singleton.clear()


def setup_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.MQTTv5)
    client.on_connect = on_connect
    client.on_message = on_message
    client.tls_set(ca_certs=CA_CERT_PATH, certfile=None, keyfile=None, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    return client

# --- Streamlit App ---
st.set_page_config(page_title="AIR-01 MQTT Stream", layout="wide")
st.title("AIR-01 Raw Sensor Data via MQTT")

st.write(f"Attempting to connect to: `{MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}`")
st.write(f"Subscribing to: `{MQTT_TOPIC_SUBSCRIBE}`")

if st.session_state.mqtt_client is None:
    st.session_state.mqtt_client = setup_mqtt_client()
    st.session_state.mqtt_client.loop_start() # Start a background thread for MQTT

# Display connection status
if st.session_state.mqtt_connected:
    st.success("MQTT Client Connected and Listening")
else:
    st.error("MQTT Client Not Connected. Check console for errors.")

st.subheader("Received Messages (Newest First):")

# Create a placeholder for messages
message_area = st.empty()

# Display messages
if st.session_state.mqtt_messages:
    messages_str = ""
    for topic, payload in st.session_state.mqtt_messages:
        messages_str += f"**Topic:** `{topic}`  
**Payload:** `{payload}`
---
"
    message_area.markdown(messages_str)
else:
    message_area.info("No messages received yet...")

# Note: The app will automatically update as messages arrive due to on_message triggering a rerun.
# For a production app, more sophisticated state management and threading might be needed.

# Keep the script running
# while True:
#    time.sleep(1)
#    if hasattr(st, 'experimental_rerun'): # Periodically ensure UI updates if no messages
#        if not st.session_state.mqtt_messages: # Only if no messages to prevent excessive reruns
#             st.experimental_rerun()


# Clean up MQTT client on script stop (optional, Streamlit handles some of this)
# def on_stop():
#    if st.session_state.mqtt_client:
#        st.session_state.mqtt_client.loop_stop()
#        st.session_state.mqtt_client.disconnect()
#        st.session_state.mqtt_messages.append(("Status", "Disconnected from MQTT Broker."))

# This part is tricky to implement reliably with Streamlit's execution model
# st.script_run_on_stop(on_stop) # Not a standard Streamlit feature

