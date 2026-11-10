-- Schéma de la base. Rejouable sans risque (IF NOT EXISTS).

-- Registre des fichiers déjà traités. Le hash SHA-256 du CONTENU identifie un fichier :
-- même contenu = même fichier, quel que soit son nom. La clé primaire interdit
-- physiquement d'enregistrer deux fois le même fichier.
CREATE TABLE IF NOT EXISTS processed_files (
    file_hash    TEXT PRIMARY KEY,
    file_name    TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Une ligne par transaction, avec le flag calculé.
CREATE TABLE IF NOT EXISTS transactions (
    id                   BIGSERIAL PRIMARY KEY,
    file_hash            TEXT NOT NULL REFERENCES processed_files (file_hash),
    datetime_transaction TIMESTAMP NOT NULL,
    iban_origine         TEXT NOT NULL,
    pays_source          CHAR(2) NOT NULL,
    banque_source        TEXT NOT NULL,
    iban_destinataire    TEXT NOT NULL,
    pays_destinataire    CHAR(2) NOT NULL,
    montant_eur          NUMERIC(14, 2) NOT NULL CHECK (montant_eur > 0),
    flagged              BOOLEAN NOT NULL
);

-- Les trois agrégats demandés, calculés PAR FICHIER (clé = fichier + IBAN/banque).
-- Pour un total global (dashboard) : SELECT iban, SUM(total_eur) ... GROUP BY iban.
CREATE TABLE IF NOT EXISTS sum_sent_by_iban (
    file_hash TEXT NOT NULL REFERENCES processed_files (file_hash),
    iban      TEXT NOT NULL,
    total_eur NUMERIC(14, 2) NOT NULL,
    PRIMARY KEY (file_hash, iban)
);

CREATE TABLE IF NOT EXISTS sum_sent_by_bank (
    file_hash TEXT NOT NULL REFERENCES processed_files (file_hash),
    bank      TEXT NOT NULL,
    total_eur NUMERIC(14, 2) NOT NULL,
    PRIMARY KEY (file_hash, bank)
);

CREATE TABLE IF NOT EXISTS sum_received_by_iban (
    file_hash TEXT NOT NULL REFERENCES processed_files (file_hash),
    iban      TEXT NOT NULL,
    total_eur NUMERIC(14, 2) NOT NULL,
    PRIMARY KEY (file_hash, iban)
);
