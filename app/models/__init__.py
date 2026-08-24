"""
SQLAlchemy models package.

Importing this package registers every model on the shared
``Base.metadata`` so Alembic autogenerate and ``create_all`` work.
"""
from app.models.academics import *  # noqa: F401, F403
from app.models.activities import *  # noqa: F401, F403
from app.models.attendance import *  # noqa: F401, F403
from app.models.behavior import *  # noqa: F401, F403
from app.models.grades import *  # noqa: F401, F403
from app.models.homework import *  # noqa: F401, F403
from app.models.notifications import *  # noqa: F401, F403
from app.models.reports import *  # noqa: F401, F403
from app.models.schedules import *  # noqa: F401, F403
from app.models.schools import *  # noqa: F401, F403
from app.models.students import *  # noqa: F401, F403
from app.models.teachers import *  # noqa: F401, F403
from app.models.users import *  # noqa: F401, F403
