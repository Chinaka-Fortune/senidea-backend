from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView
from flask_jwt_extended import jwt_required, get_jwt

class AdminModelView(ModelView):
    def is_accessible(self):
        claims = get_jwt()
        return claims.get('role') == 'Admin'

    def inaccessible_callback(self, name, **kwargs):
        return {'error': 'Admin access required'}, 403

class AdminIndex(AdminIndexView):
    @jwt_required()
    def is_accessible(self):
        claims = get_jwt()
        return claims.get('role') == 'Admin'

    def inaccessible_callback(self, name, **kwargs):
        return {'error': 'Admin access required'}, 403