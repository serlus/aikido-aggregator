-- db/seed.sql — Fase 1: seed manual do diretório (linhagens e orgs).
-- Fonte: pesquisa 2026-07 (federações, dojos e genealogia técnica).
-- Idempotente: INSERT OR IGNORE nunca sobrescreve edições manuais no banco.

-- ══════════ LINHAGENS ══════════
-- ueshiba (raiz) → aikikai → tissier_ffaaa | kawai | kumano_anno
--                → yoshinkan | iwama_saito | ki_society → yuishinkai | shodokan

INSERT OR IGNORE INTO lineages (id, name, founder, parent_id, notes) VALUES
  ('ueshiba',       'Aikido (raiz)',                   'Morihei Ueshiba (O-Sensei, 1883-1969)',  NULL,         'Fundador do Aikido'),
  ('aikikai',       'Aikikai',                         'Kisshomaru Ueshiba',                     'ueshiba',    'Linha majoritária; atual Doshu Moriteru Ueshiba (Hombu Dojo, Tóquio)'),
  ('tissier_ffaaa', 'Linha Christian Tissier / FFAAA', 'Christian Tissier (8º Dan)',             'aikikai',    'Cofundador da FFAAA (1983); rede FR-AR-CL-BR'),
  ('kawai',         'Linha Reishin Kawai',             'Reishin Kawai Shihan (8º Dan)',          'aikikai',    'Pioneiro no Brasil (1963, 1º dojo da América Latina); base de SP, PR e SC'),
  ('kumano_anno',   'Linha Kumano / Hikitsuchi-Anno',  'Michio Hikitsuchi (10º Dan)',            'aikikai',    'Kumano Juku Dojo (Shingu); sucessor Motomichi Anno; ênfase espiritual/Kototama'),
  ('yoshinkan',     'Yoshinkan',                       'Gozo Shioda (1955)',                     'ueshiba',    'Estilo rígido/marcial; IYAF'),
  ('iwama_saito',   'Iwama / Shinshin Aikishuren Kai', 'Morihiro Saito → Hitohira Saito (2004)', 'ueshiba',    'Base no dojo original de Iwama; saiu do Aikikai em 2004'),
  ('ki_society',    'Ki Society (Shin Shin Toitsu)',   'Koichi Tohei (1971/1974)',               'ueshiba',    'Separou-se do Aikikai em 1974; foco em Ki'),
  ('shodokan',      'Shodokan (Tomiki)',               'Kenji Tomiki (1967)',                    'ueshiba',    'Único estilo com competição; sede em Osaka; sem grupo organizado no BR'),
  ('yuishinkai',    'Aikido Yuishinkai',               'Koretoshi Maruyama (1996)',              'ki_society', 'Dissidência da Ki Society');

-- ══════════ ORGANIZAÇÕES — JAPÃO ══════════
INSERT OR IGNORE INTO orgs (id, name, kind, country, state, city, lineage, parent_id, url, notes) VALUES
  ('aikikai_hombu',   'Aikikai Foundation / Hombu Dojo', 'hombu', 'JP', NULL,       'Tóquio (Shinjuku)', 'aikikai',     NULL,            'https://www.aikikai.or.jp/',       'Matriz mundial; Doshu Moriteru Ueshiba'),
  ('kumano_juku',     'Kumano Juku Dojo',                'dojo',  'JP', 'Wakayama', 'Shingu',            'kumano_anno', 'aikikai_hombu', NULL,                               'Dojo onde O-Sensei ensinou; ativo; instrutor local Fujioka Sensei'),
  ('yoshinkan_honbu', 'Yoshinkan Honbu Dojo',            'hombu', 'JP', NULL,       'Tóquio',            'yoshinkan',   NULL,            'https://www.yoshinkan.net/',       'Sede mundial Yoshinkan/IYAF'),
  ('iwama_kai',       'Iwama Shinshin Aikishuren Kai',   'hombu', 'JP', 'Ibaraki',  'Iwama',             'iwama_saito', NULL,            'https://iwamashinshinaikido.com/', 'Hitohira Saito'),
  ('yuishinkai_jp',   'Aikido Yuishinkai',               'hombu', 'JP', NULL,       NULL,                'yuishinkai',  NULL,            'https://aikidoyuishinkai.org/',    NULL);

-- ══════════ ORGANIZAÇÕES — FRANÇA ══════════
INSERT OR IGNORE INTO orgs (id, name, kind, country, state, city, lineage, parent_id, url, notes) VALUES
  ('ffaaa',          'FFAAA — Fédération Française d''Aïkido, Aïkibudo et Affinitaires', 'federation', 'FR', NULL, 'Paris', 'tissier_ffaaa', NULL, 'https://www.aikido.com.fr/', 'Fundada 1983; maior grupo de aikido da França'),
  ('cercle_tissier', 'Cercle Tissier', 'dojo', 'FR', NULL, 'Vincennes', 'tissier_ffaaa', 'ffaaa', 'https://www.cercletissier.com/', '108 rue de Fontenay; centro multi-artes desde 1976; agenda oficial de estágios em christiantissier.com');

-- ══════════ ORGANIZAÇÕES — BRASIL ══════════
INSERT OR IGNORE INTO orgs (id, name, kind, country, state, city, lineage, parent_id, url, notes) VALUES
  ('febrai',         'FEBRAI — Federação Brasileira de Aikido',                    'federation',    'BR', 'RJ', NULL,                  'aikikai',       'aikikai_hombu', 'https://aikidofebrai.com.br/',          'Fundada 1997 (Severino Sales); reconhecida pelo Hombu em 2009; linha Yamada até 2019'),
  ('fepai',          'FEPAI-Brasil — Federação Paulista de Aikido',                'federation',    'BR', 'SP', 'São Paulo',           'aikikai',       'aikikai_hombu', 'https://www.fepai.org.br/',             'Fundada 1978; única reconhecida pela IAF; presidida por Makoto Nishida Shihan'),
  ('takemussu',      'Instituto Takemussu / Brazil Aikikai',                       'confederation', 'BR', 'SP', 'São Paulo',           'aikikai',       'aikikai_hombu', 'http://aikikai.org.br/',                'Wagner Bull Shihan 7º Dan; reconhecido pelo Hombu p/ exames Yudansha'),
  ('shoyukan_br',    'Shoyukan Aikikai Brasil / Círculo Aikido Leoni',             'institute',     'BR', 'RJ', 'Rio de Janeiro',      'tissier_ffaaa', NULL,            'https://shoyukanaikikaibrasil.com.br/', 'Luc Leoni Sensei (FFAAA) desde 2000; exames Yudansha desde 2020'),
  ('aikido_parana',  'Aikido Paraná Brasil (Federação PR)',                        'federation',    'BR', 'PR', NULL,                  'kawai',         NULL,            'https://aikidoparanabrasil.com.br/',    'Desde 1995; 250+ graduados'),
  ('abai',           'ABAI — Federação Baiana de Aikido',                          'federation',    'BR', 'BA', NULL,                  'aikikai',       NULL,            'https://www.aikidoba.com.br/',          NULL),
  ('fma',            'Federação Mineira de Aikido',                                'federation',    'BR', 'MG', NULL,                  'aikikai',       NULL,            'https://www.minasaikido.com.br/',       'Cadastro formal de alunos (ficha + anuidade)'),
  ('ica',            'ICA — Instituto Catarinense de Aikido',                      'institute',     'BR', 'SC', 'Florianópolis',       'kawai',         NULL,            'https://aikidokas.com.br/',             'Fundado 2017; ~100 associados; presidente Carlos Grisalt 6º Dan; 3 dojos filiados'),
  ('acai',           'ACAI — Associação Catarinense de Aikidō',                    'federation',    'BR', 'SC', 'Florianópolis',       'kawai',         NULL,            'http://www.aikidosc.org.br/',           'Linhagem Kawai via Pádua Sensei; site renovado out/2025'),
  ('inst_fornazier', 'Instituto Fornazier de Aikido',                              'institute',     'BR', 'SC', 'Blumenau',            'kawai',         NULL,            NULL,                                    'Valdecir Fornazier 6º Dan, designado por Kawai em 1999 p/ SC; matriz do Vale do Itajaí'),
  ('aikido_itajai',  'Aikido Itajaí Vila Operária',                                'dojo',          'BR', 'SC', 'Itajaí',              'kawai',         'inst_fornazier', NULL,                                   'Sensei Fernando Fiedler 5º Dan desde 2008; treinos Univali e academia Lótus'),
  ('aabc_bc',        'AABC — Associação de Aikido de Balneário Camboriú',          'dojo',          'BR', 'SC', 'Balneário Camboriú',  'kawai',         'inst_fornazier', NULL,                                   'Mário Tetto 3º Dan; treinou no Cercle Tissier 2010-2011; direção técnica Fornazier desde 2002'),
  ('daisho',         'Daishō Aikido Dojo',                                         'dojo',          'BR', 'SC', 'Criciúma',            'kawai',         NULL,            'https://www.aikidocriciuma.com.br/',    'Sensei Cristiano Salomão 4º Dan; desde 2011'),
  ('chikarasin',     'Chikarasin Dojo',                                            'dojo',          'BR', 'SC', 'Blumenau',            'aikikai',       'fepai',         NULL,                                    'Sensei Wellington de Souza; filiado FEPAI'),
  ('tachibana',      'Instituto Tachibana de Aikido',                              'dojo',          'BR', 'SC', 'Joinville',           'aikikai',       NULL,            NULL,                                    'Sensei Rafael Rochadel; desde 2015'),
  ('bunsei',         'Bunsei Dojo',                                                'dojo',          'BR', 'SC', 'Florianópolis',       'kawai',         'acai',          NULL,                                    'Sede dos treinos de Pádua Sensei, introdutor do aikido em SC'),
  ('ame_no_iwaya',   'Dojô Ame no Iwaya',                                          'dojo',          'BR', 'RS', 'Viamão',              'kumano_anno',   NULL,            'https://www.aikido-amenoiwaya.com.br/', 'Olga Curado, aluna de Keizen Ono e Motomichi Anno; nome dado por Anno Sensei; desde 2019'),
  ('uniao_hikari',   'União Hikari Aikido Renshinkai do Brasil',                   'institute',     'BR', 'SP', 'Osasco',              'yoshinkan',     NULL,            NULL,                                    'Fundador Eduardo Pinto Shihan (falecido 01/2025); 1º filiado latino-americano da IYAF (1992)'),
  ('shukikan',       'Shukikan Dojo (Ki-Aikido Curitiba)',                         'dojo',          'BR', 'PR', 'Curitiba',            'ki_society',    NULL,            NULL,                                    'Linhagem alternativa mais próxima de SC');

-- ══════════ ORGANIZAÇÕES — ARGENTINA / CHILE ══════════
INSERT OR IGNORE INTO orgs (id, name, kind, country, state, city, lineage, parent_id, url, notes) VALUES
  ('circulo_aikikai', 'Círculo Aikikai (Argentina)', 'federation', 'AR', NULL, 'Córdoba',      'tissier_ffaaa', NULL, 'https://www.circuloaikikai.com.ar/', 'Diretor Luis Colalillo; subordinado internacionalmente a Tissier; dojos em Córdoba, Santa Fe, Mendoza, Buenos Aires'),
  ('aaa_argentina',   'Aikido Aikikai Argentina',    'federation', 'AR', NULL, 'Buenos Aires', 'tissier_ffaaa', NULL, NULL,                                 'Orientação de Tissier; reconhecida pelo Hombu desde 2022'),
  ('fedenachaa',      'FEDENACHAA (Chile)',          'federation', 'CL', NULL, 'Santiago',     'tissier_ffaaa', NULL, 'https://www.fedenachaa.cl/',         'Vinculada ao Cercle Tissier e à IAF');

-- ══════════ ORGS NOVAS + INSTAGRAM (2026-07-27 — perfis indicados pelo mantenedor) ══════════
-- instagram = handle sem @; usado APENAS como link no diretório (nunca coleta —
-- robots/ToS do Instagram proíbem acesso automatizado; cf. FASES Fase 8).
INSERT OR IGNORE INTO orgs (id, name, kind, country, state, city, lineage, parent_id, url, instagram, notes) VALUES
  ('fechiai',            'FECHIAI — Federación Chilena de Aikido',      'federation', 'CL', NULL, 'Santiago',        'aikikai',       NULL,             'https://fechiai.cl/',                'federacionchilenadeaikido', 'Desde 2002; rede de dojos e seminários; distinta da FEDENACHAA'),
  ('minami_no_tani',     'Minami no Tani Dojo',                         'dojo',       'BR', 'SC', 'Jaraguá do Sul',  'aikikai',       'tachibana',      NULL,                                 'minami_no_tani_dojo',       'Dojo de aikido de Jaraguá do Sul, ligado ao Instituto Tachibana'),
  ('okinaie',            'Õkinaie Dojo',                                'dojo',       'BR', 'SC', 'Criciúma',        NULL,            NULL,             'https://okinaie.com.br/',            'okinaie.artesmarciais',     'Desde 2015; aikido e defesa pessoal; método próprio de ensino'),
  ('aikido_caxias',      'Aikido Caxias do Sul',                        'dojo',       'BR', 'RS', 'Caxias do Sul',   NULL,            NULL,             NULL,                                 'aikidocaxiasdosul',         'Identificado via Instagram; linhagem e instrutor a confirmar'),
  ('canal_aikido_br',    'Canal Aikido Brasil',                         'media',      'BR', NULL, NULL,              NULL,            NULL,             'https://www.youtube.com/c/AikidoBrasil', 'canal.aikidobrasil',    'Ricardo Miyajima; pesquisa sobre técnica, história e formação no aikido'),
  ('bruno_gonzalez',     'Bruno Gonzalez Sensei (6º Dan)',              'instructor', 'FR', NULL, 'Paris',           'tissier_ffaaa', 'cercle_tissier', 'https://aikido-brunogonzalez.com/',  'gonzalez_bruno_aikido_official', 'Instrutor do Cercle Tissier, formado por Christian Tissier');

UPDATE orgs SET instagram = 'aikido_ffaaa'    WHERE id = 'ffaaa'    AND instagram IS NULL;
UPDATE orgs SET instagram = 'aikidokas.brasil' WHERE id = 'ica'     AND instagram IS NULL;
