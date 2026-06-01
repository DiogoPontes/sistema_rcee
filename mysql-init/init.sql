CREATE DATABASE IF NOT EXISTS rcee_cadastro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS rcee_admin_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS rcee_consulta_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'rcee_user'@'%' IDENTIFIED WITH mysql_native_password BY 'rcee123';

GRANT ALL PRIVILEGES ON rcee_cadastro_db.* TO 'rcee_user'@'%';
GRANT ALL PRIVILEGES ON rcee_admin_db.* TO 'rcee_user'@'%';
GRANT ALL PRIVILEGES ON rcee_consulta_db.* TO 'rcee_user'@'%';

FLUSH PRIVILEGES;