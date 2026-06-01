-- --------------------------------------------------------
-- Servidor:                     10.1.140.15
-- Versão do servidor:           10.1.29-MariaDB - MariaDB Server
-- OS do Servidor:               Linux
-- HeidiSQL Versão:              12.7.0.6850
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Copiando estrutura do banco de dados para rcee
CREATE DATABASE IF NOT EXISTS `rcee_consulta_bkp` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `rcee_consulta_bkp`;

-- Copiando estrutura para tabela rcee.alembic_version
CREATE TABLE IF NOT EXISTS `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Copiando dados para a tabela rcee.alembic_version: ~0 rows (aproximadamente)
INSERT IGNORE INTO `alembic_version` (`version_num`) VALUES
	('b41aefb56077');

-- Copiando estrutura para tabela rcee.category
CREATE TABLE IF NOT EXISTS `category` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(160) NOT NULL,
  `slug` varchar(180) NOT NULL,
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8;

-- Copiando dados para a tabela rcee.category: ~8 rows (aproximadamente)
INSERT IGNORE INTO `category` (`id`, `name`, `slug`, `description`) VALUES
	(1, 'Crime Organizado (CO)', 'crime-organizado', NULL),
	(2, 'Tecnologias Inovadoras / Disruptivas', 'tecnologias-inovadoras', NULL),
	(3, 'Eventos Climáticos Extremos', 'eventos-climaticos', NULL),
	(4, 'Infraestruturas Críticas / Estratégicas', 'infraestruturas-criticas', NULL),
	(5, 'Logística de Defesa – Base Industrial de Defesa (BID)', 'logistica-defesa-bid', NULL),
	(6, 'Gestão Pública', 'gestao-publica', NULL),
	(7, 'Conjunturas e Cenários', 'conjunturas-cenarios', NULL);

-- Copiando estrutura para tabela rcee.post
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
  KEY `ix_post_status` (`status`),
  CONSTRAINT `post_ibfk_1` FOREIGN KEY (`author_id`) REFERENCES `user` (`id`),
  CONSTRAINT `post_ibfk_2` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8;

-- Copiando dados para a tabela rcee.post: ~4 rows (aproximadamente)
INSERT IGNORE INTO `post` (`id`, `title`, `slug`, `summary`, `body`, `status`, `category_id`, `author_id`, `published_at`, `created_at`, `updated_at`, `featured_image`) VALUES
	(4, 'Gestão de Crises: Liderança, Resolução e Comunicação Estratégica', 'sdfsdfsdfsdfsdf', 'Crises não esperam, você está pronto? Responda como um líder, antecipe riscos, comunique com precisão e proteja a reputação.', '<p><strong>Sobre o curso&nbsp;</strong></p><p>Capacite-se com uma formação multidisciplinar focada na prevenção, gerenciamento e resolução de crises corporativas. Desenvolva habilidades para antecipar, monitorar e responder a crises, utilizando Inteligência Artificial e Big Data. Com uma visão holística e profunda, o curso enfatiza estratégias para proteger e fortalecer a reputação da organização nos momentos mais desafiadores.</p><p><strong>Para quem é?</strong></p><p>• Este curso é pensado para profissionais como você, focados em riscos corporativos e gestão de crises, que desejam atualizar conhecimentos sobre tecnologias emergentes e práticas contemporâneas de resolução de problemas.</p><p>• Também para especialistas em comunicação corporativa, marketing e relações públicas que buscam aprimorar estratégias para gerenciar crises e proteger a reputação da marca.</p><p>• Assim como executivos e gestores de médio a alto escalão que precisam liderar equipes em cenários de crise, tomar decisões ágeis e implementar planos de contingência.</p><p><strong>Resultados esperados&nbsp;</strong></p><p>• Desenvolva habilidades para liderar em cenários de crise</p><p>• Domine estratégias de comunicação transparente e empática</p><p>• Utilize tecnologias emergentes para prevenção e resolução de crises</p><p>• Torne-se capaz de criar e implementar planos de contingência</p><p>• Desenvolva visão estratégica e pensamento sistêmico</p>', 'published', 6, 1, '2025-11-07 15:13:13', '2025-11-07 15:08:19', '2025-11-10 17:46:22', 'static/uploads/gestaopublica.jpg'),
	(5, 'Como a Comunicação Organizacional Estratégica Impacta na Responsabilidade Empresarial?', 'teste-titulo', 'A comunicação organizacional estratégica desempenha um papel fundamental no panorama atual dos negócios, contribuindo significativamente para a sustentabilidade empresarial e a responsabilidade social das organizações.', '<h2>O que é Comunicação Organizacional Estratégica?</h2><p>A Comunicação Organizacional Estratégica é uma abordagem da comunicação adotada pelas organizações para alcançar seus objetivos estratégicos e fortalecer sua posição no mercado.</p><p>Ela envolve o planejamento, desenvolvimento e implementação de estratégias de comunicação alinhadas com os objetivos organizacionais e as necessidades de seus públicos-alvo.</p><p>A Comunicação Organizacional Estratégica vai além da simples transmissão de informações, buscando criar relacionamentos sólidos e duradouros com clientes, colaboradores, acionistas e outras partes interessadas.</p><p>Por meio da Comunicação Organizacional Estratégica, as empresas podem construir e manter uma imagem corporativa positiva, promover a confiança e a credibilidade, gerenciar crises de reputação, promover o engajamento dos colaboradores e demonstrar seu compromisso com a responsabilidade social corporativa.</p><p>Isso envolve a criação de mensagens claras e consistentes, o uso eficaz de diferentes canais de comunicação e a gestão proativa das relações com stakeholders internos e externos.</p><p>No contexto da sustentabilidade empresarial e responsabilidade social, a comunicação organizacional estratégica desempenha um papel crucial na disseminação de informações sobre as práticas e iniciativas sustentáveis da empresa, bem como na promoção do engajamento e participação dos stakeholders em ações sociais e ambientais.</p>', 'published', 2, 1, '2025-11-10 16:53:33', '2025-11-10 16:53:33', '2025-11-10 17:05:34', 'static/uploads/a27ea-comuicacao-organizacional.jpg'),
	(7, 'OPERAÇÃO ATLAS 2025', 'operacao-atlas-2025-1762808672', 'Forças Armadas iniciaram a Fase 1 da Operação Atlas 2025\r\nO Exercício conjunto visa aprimorar a coordenação logística e o deslocamento estratégico das Forças Armadas para cenários operacionais complexos', '<p>Teve início nesta segunda-feira (30/06), na Escola Superior de Defesa (ESD), em Brasília (DF), a Fase 1 da Operação Atlas 2025. A cerimônia de abertura contou com a presença do Chefe do Estado-Maior Conjunto das Forças Armadas (EMCFA), Almirante de Esquadra Renato Rodrigues de Aguiar Freire, acompanhado pelo Chefe de Operações Conjuntas do Estado-Maior Conjunto das Forças Armadas, Tenente-Brigadeiro do Ar Walcyr Josué de Castilho Araujo, e pelo Comandante de Preparo (COMPREP), Tenente-Brigadeiro do Ar Raimundo Nogueira Lopes Neto. Também participaram Oficiais-Generais da Marinha do Brasil (MB), do Exército Brasileiro (EB), da Força Aérea Brasileira (FAB), representantes do Ministério das Relações Exteriores e demais autoridades convidadas</p><p>.<img src="https://www.fab.mil.br/sis/enoticias/imagens/pub/49167/i2563014551405880.jpg"></p><p><br></p><p>A Operação Atlas 2025 tem como objetivo identificar oportunidades de melhoria e desafios relacionados ao planejamento, coordenação e execução do deslocamento estratégico das capacidades de Defesa para um Teatro de Operações na Região Amazônica. A missão considera, entre outros fatores, a compatibilidade da infraestrutura logística nacional com os meios operacionais das Forças Armadas. Além disso, busca promover o treinamento conjunto das Forças Singulares, com foco no aprimoramento da interoperabilidade e no fortalecimento dos sistemas de Comando e Controle, em um ambiente operacional complexo e desafiador.</p><p><img src="https://www.fab.mil.br/sis/enoticias/imagens/pub/49167/i2563014073706103.jpg"></p><p>Durante a abertura da Fase 1 da Operação Atlas 2025, o Chefe do Estado-Maior Conjunto das Forças Armadas, Almirante de Esquadra Renato Rodrigues de Aguiar Freire, destacou a importância estratégica do exercício.&nbsp;“A Operação Atlas representa um novo marco na defesa nacional. É mais do que um adestramento&nbsp;é uma oportunidade real de fortalecer a interoperabilidade, testar nossas capacidades logísticas e planejar, de forma integrada, a atuação das Forças Armadas diante dos desafios atuais. Estamos diante de uma operação sem precedentes no Brasil, que exige profissionalismo, comprometimento e visão estratégica. A história será escrita por quem souber planejar, executar e aprender com excelência”, afirmou.</p><p><img src="https://www.fab.mil.br/sis/enoticias/imagens/pub/49167/i2563014073206922.jpg"></p><p>O exercício será desenvolvido entre os meses de junho e outubro, com atividades concentradas em uma das regiões mais desafiadoras do território brasileiro. A operação está estruturada em três fases:</p><p><strong>Fase 1 (30/06&nbsp;a 11/07):</strong> realização do planejamento conjunto na ESD, com definição de estratégias, integração de ações e ambientação dos participantes;</p><p><strong>Fase 2 (27/09 a 01/10):</strong> deslocamento estratégico de meios e efetivo para a Amazônia;</p><p><strong>Fase 3 (02 a 11/10):</strong> execução de atividades táticas em ambientes terrestre, aquático e aéreo, exigindo elevado desempenho logístico e capacidade de atuação em longas distâncias.</p><p><img src="https://www.fab.mil.br/sis/enoticias/imagens/pub/49167/i2563014551104646.jpg"></p><p>"A Operação Atlas é uma operação conjunta que conta com a colaboração de todas as Forças Armadas. Especificamente para a Força Aérea, o objetivo é treinar o deslocamento estratégico. Ou seja, como reunimos todos os meios da Força Aérea necessários para uma operação em um teatro amazônico e como chegamos até lá? Portanto, todo o planejamento é necessário para que possamos colocar os meios em prontidão e em condições de atuar no teatro de operações. Esse planejamento, naturalmente, é bastante complexo, devido aos inúmeros detalhes e às dificuldades inerentes à região amazônica", explicou o&nbsp;Chefe de Operações Conjuntas do Estado-Maior Conjunto das Forças Armadas, Tenente-Brigadeiro do Ar Walcyr.</p><p>A programação da fase inicial inclui apresentações sobre inteligência estratégica, integração operacional, logística, segurança orgânica e medidas administrativas. Ao final, os participantes serão distribuídos em salas de planejamento, onde desenvolverão as diretrizes para as fases seguintes da operação.</p><p><img src="https://www.fab.mil.br/sis/enoticias/imagens/pub/49167/i2563014074502032.jpg"></p><p>“Esta Escola de Altos Estudos sente-se honrada em sediar a Fase 1 da Operação Atlas 2025, dedicada ao planejamento e às ações de comunicação estratégica. É motivo de orgulho fazer parte do primeiro exercício de adestramento logístico conjunto do Ministério da Defesa, coordenado pelo Estado-Maior Conjunto das Forças Armadas. Contem com o apoio do efetivo e com toda a estrutura da Escola Superior de Defesa para contribuir com o pleno êxito da Operação Atlas 2025”, destacou a Comandante da ESD, Major-Brigadeiro Médica Carla Lyrio Martins.</p>', 'published', 5, 1, '2025-11-10 18:09:00', '2025-11-10 18:04:32', '2025-11-19 16:29:51', 'static/uploads/atlas_1.jpg');

-- Copiando estrutura para tabela rcee.post_asset
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
  KEY `ix_post_asset_post_id` (`post_id`),
  CONSTRAINT `post_asset_ibfk_1` FOREIGN KEY (`post_id`) REFERENCES `post` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8;

-- Copiando dados para a tabela rcee.post_asset: ~4 rows (aproximadamente)
INSERT IGNORE INTO `post_asset` (`id`, `post_id`, `asset_type`, `title`, `url`, `file_path`, `meta_json`, `created_at`) VALUES
	(5, 5, 'news_link', 'Como a Comunicação Organizacional Estratégica Impacta na Responsabilidade Empresarial?', 'https://www.posuscs.com.br/como-a-comunicacao-organizacional-estrategica-contribui-para-a-sustentabilidade-empresarial-e-respon/noticia/3005', NULL, NULL, '2025-11-10 17:04:57'),
	(9, 4, 'news_link', 'Gestão de Crises', 'https://posdigital.pucpr.br/cursos/gestao-de-crises?utm_source=google&utm_medium=cpc&utm_campaign=pucpr_prf_ins_aon_search_pos-grad_br_g_gestao-crise&utm_group=c_12062_gestao-crise_search_pos-grad_int_termos-amplos&utm_content=c_12062_gestao-crise_search_pos-grad_g_g_g&gad_source=1&gad_campaignid=22284976235&gclid=CjwKCAiAt8bIBhBpEiwAzH1w6SimNOIZo353y5NFsmrJzhnDUYyu5K9pb9GCDaVxWRs2NXvpF7WstxoCW_kQAvD_BwE', NULL, NULL, '2025-11-10 17:43:06'),
	(12, 7, 'video_link', 'Forças Armadas iniciaram Fase 1 da Operação Atlas', 'https://www.youtube.com/shorts/iOi8dj6vpFA?feature=share', NULL, NULL, '2025-11-10 18:05:03');

-- Copiando estrutura para tabela rcee.user
CREATE TABLE IF NOT EXISTS `user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `instituicao` varchar(100) DEFAULT NULL,
  `contato` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;

-- Copiando dados para a tabela rcee.user: ~5 rows (aproximadamente)
INSERT IGNORE INTO `user` (`id`, `name`, `email`, `password_hash`, `role`, `is_active`, `created_at`, `instituicao`, `contato`) VALUES
	(1, 'Diogo Pontes', 'diogopontes.silva@eb.mil.br', 'scrypt:32768:8:1$tUT9lcs0mJ476RgW$1e3a922b2ef162df0a9c4481f41a39e105d0845ff63f2ea730f0240b540db0558f881d3e910e0d53f4a639b28122257bfef35712358b87a9be141e92ba8a83d0', 'Admin', 1, '2025-11-06 17:20:18', 'EB - CML', '(21) 99935-7755'),
	(2, 'Meireles', 'meireles.leonardo@eb.mil.br', 'scrypt:32768:8:1$Fyz9jBCdrl71M0yB$00f7bfff154e46097f7d25f08ac3c548e41d3a836ff0870c5ffcea89c8f9da0d59dcbb9dfd1829ed1e734e67390c900efcc239bedcdf1222c21c6f82dc9f8d47', 'Editor', 1, '2025-11-07 11:43:30', NULL, NULL),
	(3, 'Nicole', 'nicole.sales@eb.mil.br', 'scrypt:32768:8:1$sDO2TEkImBpzJaxe$db9687ffe7a93ab8df3a609f6b463190e90374db32d51bdf0d19cfbc5e7cee5511d6f529f1bb9c8e0df15a2519eafa30ca44d370732fea3c28e7f4701b56d936', 'Admin', 1, '2025-11-10 19:06:00', 'EB - 1ª RM', NULL),
	(7, 'Gen Moreno', 'moreno@eb.mil.br', 'scrypt:32768:8:1$qGRZJVdykHDJt63G$3f42a241724a25d8e54ca253d129e9f5a7312525a539f97a0ebe3aadd349ee286a7435d00c9e378ce737fe63dcafa7da238e2dcd3fafadd3a876518c613ee89b', 'Admin', 1, '2025-11-19 16:28:19', 'EB - CML', NULL),
	(8, 'nicole', 'nicolesales2112@gmail.com', 'scrypt:32768:8:1$mpn68wYGKiTZhbgp$f64ebb1a296d2cad20ff1e164d7688cfa94a7ac3fa745002c66712b831cb4a40bd6ce37ccfda8ea3529d0cb66161063f380868438aa3e094d0b7bccf3c38de54', 'Admin', 1, '2025-12-08 15:27:40', NULL, NULL),
	(9, 'lopes', 'lopes@gmail.com', 'scrypt:32768:8:1$983r2qEA2Vnnl3CO$e3daf7ed9c56a62b1569e7174cce8806b763aab67d29d7d8674b51e96b72b14ec94f7cb76db5399304285f10e0a29a37b70f6dd9331d13fc5b652e6645910100', 'Admin', 1, '2025-12-08 15:31:21', NULL, NULL);

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
