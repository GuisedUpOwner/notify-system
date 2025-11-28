from sqlalchemy import text



def get_user(db, user_id):
    result = db.execute(
        text("""
            SELECT id, name, username,
                   (SELECT name FROM phases WHERE id = users.current_phase) AS current_phase_name
            FROM users
            WHERE id = :uid
        """),
        {"uid": user_id}
    )
    return result.mappings().first()

def get_friends(db, user_id):
    result = db.execute(
        text("""
            SELECT DISTINCT u.id, u.push_token
            FROM users u
            
            -- outgoing accepted friend requests
            INNER JOIN friends fr1 
                ON fr1.friend_id = u.id
                AND fr1.user_id = :uid
                AND fr1.request_status = 'accept'
            
            UNION

            SELECT DISTINCT u2.id, u2.push_token
            FROM users u2
            
            -- incoming accepted friend requests
            INNER JOIN friends fr2
                ON fr2.user_id = u2.id
                AND fr2.friend_id = :uid
                AND fr2.request_status = 'accept'
        """),
        {"uid": user_id}
    )

    return result.mappings().all()

def get_user_by_name(db, name):
    result = db.execute(
        text("""
            SELECT id, name, username,
                   (SELECT name FROM phases WHERE id = users.current_phase) AS current_phase_name
            FROM users
            WHERE name = :name
        """),
        {"name": name}
    )
    return result.mappings().first()

def get_user_by_username(db, username):
    result = db.execute(
        text("""
            SELECT id, name, username,
                   (SELECT name FROM phases WHERE id = users.current_phase) AS current_phase_name
            FROM users
            WHERE username = :username
        """),
        {"username": username}
    )
    return result.mappings().first()

