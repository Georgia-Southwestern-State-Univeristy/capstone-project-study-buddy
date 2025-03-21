"""Initialize Flask blueprints."""
"""step 1: Import the required libraries"""
from .auth import auth_routes
from .AI import ai_routes
from .user_profile import user_routes
from .translator import translator_routes
from .quiz_ai import quiz_ai_routes
from .group import groups_routes
from .group_post import group_posts_routes
from .resume import resume_routes
from .AI_avtar import ai_avtar_routes

"""step 2: Define the register_blueprints function"""
def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(auth_routes)
    app.register_blueprint(ai_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(translator_routes)
    app.register_blueprint(quiz_ai_routes)
    app.register_blueprint(groups_routes)
    app.register_blueprint(group_posts_routes)
    app.register_blueprint(resume_routes)
    app.register_blueprint(ai_avtar_routes)


    
    