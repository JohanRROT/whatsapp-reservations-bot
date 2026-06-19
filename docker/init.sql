DO $$ BEGIN
  CREATE USER whatsapp_bot_user WITH PASSWORD '64JVzt6sAu7gmpy2hZP0Jg==';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT ALL PRIVILEGES ON DATABASE whatsapp_bot_db TO whatsapp_bot_user;

CREATE TABLE conversations (
	    id SERIAL PRIMARY KEY,
	    phone_number VARCHAR(20) NOT NULL,
	    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
	    content TEXT NOT NULL,
	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
	);
	
CREATE INDEX idx_conversations_phone_created ON conversations (phone_number, created_at);

CREATE TABLE reservations ( 
	id SERIAL PRIMARY KEY, 
	phone_number VARCHAR(20) NOT NULL,
	space_type VARCHAR(20) NOT NULL CHECK (space_type IN 
	('hot_desk','private_office', 'meeting_room')), 
	start_time TIMESTAMPTZ NOT NULL, 
	end_time TIMESTAMPTZ NOT NULL CHECK (end_time > start_time), 
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() 
	);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO whatsapp_bot_user;
