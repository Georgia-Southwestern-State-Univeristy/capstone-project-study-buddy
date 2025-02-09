# Import required modules
from flask_socketio import SocketIO

# Set up Flask-SocketIO with proper configurations
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
