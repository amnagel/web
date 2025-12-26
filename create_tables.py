from Market import app, db
from Market import models  # важно: чтобы CartItem был импортирован

with app.app_context():
    db.create_all()
    print("Tables created")
