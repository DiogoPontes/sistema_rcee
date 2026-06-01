-- --------------------------------------------------------
-- Servidor:                     RCEE Docker
-- Banco:                        rcee_cadastro_db
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Garantir banco e selecionar
CREATE DATABASE IF NOT EXISTS `rcee_cadastro_db` CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `rcee_cadastro_db`;

-- --------------------------------------------------------
-- Tabela: category
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `category` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(160) NOT NULL,
  `slug` varchar(180) NOT NULL,
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: post
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `post` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(220) NOT NULL,
  `slug` varchar(240) DEFAULT NULL,
  `summary` varchar(600) DEFAULT NULL,
  `body` text,
  `status` varchar(20) DEFAULT NULL,
  `category_id` int(11) NOT NULL,
  `author_id` int(11) NOT NULL,
  `published_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `featured_image` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_post_slug` (`slug`),
  KEY `ix_post_author_id` (`author_id`),
  KEY `ix_post_category_id` (`category_id`),
  KEY `ix_post_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=166 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: post_asset
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `post_asset` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `post_id` int(11) NOT NULL,
  `asset_type` varchar(20) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `url` varchar(1024) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `meta_json` text,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_post_asset_asset_type` (`asset_type`),
  KEY `ix_post_asset_post_id` (`post_id`)
) ENGINE=InnoDB AUTO_INCREMENT=248 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: post_staging
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `post_staging` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `uuid_publicacao` varchar(36) DEFAULT NULL COMMENT 'UUID único para evitar duplicação ao publicar',
  `title` varchar(220) NOT NULL,
  `slug` varchar(240) DEFAULT NULL,
  `summary` varchar(600) DEFAULT NULL,
  `body` text,
  `status` varchar(20) NOT NULL DEFAULT 'rascunho' COMMENT 'rascunho, em_revisao, aprovado, reprovado',
  `category_id` int(11) NOT NULL,
  `author_id` int(11) NOT NULL,
  `featured_image` varchar(255) DEFAULT NULL,
  `observacao_admin` text COMMENT 'Feedback do admin em caso de reprovação',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `submitted_at` datetime DEFAULT NULL COMMENT 'Quando foi enviado para revisão',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid_publicacao` (`uuid_publicacao`),
  KEY `ix_post_staging_author_id` (`author_id`),
  KEY `ix_post_staging_category_id` (`category_id`),
  KEY `ix_post_staging_status` (`status`),
  CONSTRAINT `post_staging_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: post_asset_staging
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `post_asset_staging` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `post_staging_id` int(11) NOT NULL,
  `asset_type` varchar(20) NOT NULL COMMENT 'news_link, video_link, document, etc.',
  `title` varchar(200) DEFAULT NULL,
  `url` varchar(1024) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `meta_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_post_asset_staging_asset_type` (`asset_type`),
  KEY `ix_post_asset_staging_post_id` (`post_staging_id`),
  CONSTRAINT `post_asset_staging_ibfk_1` FOREIGN KEY (`post_staging_id`) REFERENCES `post_staging` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: staging_log
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `staging_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `post_staging_id` int(11) DEFAULT NULL,
  `action` varchar(50) NOT NULL COMMENT 'criado, editado, enviado_revisao, aprovado, reprovado, publicado',
  `user_id` int(11) NOT NULL,
  `observacao` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_staging_log_post_id` (`post_staging_id`),
  KEY `ix_staging_log_action` (`action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: user
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(512) NOT NULL,
  `role` varchar(20) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `instituicao` varchar(100) DEFAULT NULL,
  `contato` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Tabela: user_ref
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_ref` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(255) NOT NULL,
  `instituicao` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_ref_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------
-- Usuário administrador padrão
-- --------------------------------------------------------
INSERT INTO `user`
  (`name`, `email`, `password_hash`, `role`, `is_active`, `created_at`, `instituicao`, `contato`)
SELECT
  'Administrador Sistema',
  'admin@rcee.local',
  'scrypt:32768:8:1$q0cbUryIxRu7dKju$40641bfcbcd9e38764f30de542bea704b78d99cc0e3da28f589d197aad5f599ced2dec8b9a88aa0e7a12aab58417e506cc2dd06501832efd8d2a55512ee135bc',
  'Admin',
  1,
  NOW(),
  'RCEE',
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM `user` WHERE `email` = 'admin@rcee.local'
);

-- --------------------------------------------------------
-- Categorias padrão
-- --------------------------------------------------------
INSERT INTO `category` (`id`, `name`, `slug`, `description`) VALUES
	(1, 'Crime Organizado (CO) e Segurança Pública', 'crime-organizado', NULL),
	(2, 'Tecnologias Inovadoras / Disruptivas', 'tecnologias-inovadoras', NULL),
	(3, 'Eventos Climáticos Extremos', 'eventos-climaticos', NULL),
	(4, 'Infraestruturas Críticas / Estratégicas', 'infraestruturas-criticas', NULL),
	(5, 'Logística de Defesa – Base Industrial de Defesa (BID)', 'logistica-defesa-bid', NULL),
	(6, 'Gestão Pública', 'gestao-publica', NULL),
	(7, 'Conjunturas e Cenários', 'conjunturas-cenarios', NULL),
	(8, 'Resenhas e Artigos', 'resenhas', NULL),
	(9, 'EPLM', 'eplm', NULL),
	(10, 'Geração de Força', 'geracao_forca', NULL);

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;