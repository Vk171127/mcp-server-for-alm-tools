-- ALM Traceability Database Schema
-- PostgreSQL schema for managing traceability between ALM platform items

-- Create enum for ALM platform types
CREATE TYPE alm_platform_type AS ENUM (
    'azure_devops',
    'jira'
);

-- Create the sessions table (if not exists) with alm_type
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    alm_type alm_platform_type NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create requirements table (if not exists) 
CREATE TABLE IF NOT EXISTS requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    alm_type alm_platform_type NOT NULL,
    external_id VARCHAR(255), -- ID in the ALM system
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create test_cases table (if not exists)
CREATE TABLE IF NOT EXISTS test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    alm_type alm_platform_type NOT NULL,
    external_id VARCHAR(255), -- ID in the ALM system
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create the main traceability_links table
CREATE TABLE traceability_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source item
    source_type VARCHAR(50) NOT NULL, -- 'session', 'requirement', 'test_case'
    source_id VARCHAR(255) NOT NULL,
    source_alm_type alm_platform_type,
    source_external_id VARCHAR(255), -- External ID in ALM system (optional)
    
    -- Target item  
    target_type VARCHAR(50) NOT NULL, -- 'session', 'requirement', 'test_case'
    target_id VARCHAR(255) NOT NULL,
    target_alm_type alm_platform_type,
    target_external_id VARCHAR(255), -- External ID in ALM system (optional)
    
    -- Relationship metadata
    relationship_type VARCHAR(50) NOT NULL, -- 'tests', 'covers', 'implements', 'relates_to'
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Status and audit
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    
    -- Constraints
    UNIQUE(source_type, source_id, target_type, target_id, relationship_type)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_traceability_source ON traceability_links (source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_traceability_target ON traceability_links (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_traceability_relationship ON traceability_links (relationship_type);
CREATE INDEX IF NOT EXISTS idx_traceability_status ON traceability_links (status);
CREATE INDEX IF NOT EXISTS idx_traceability_alm_types ON traceability_links (source_alm_type, target_alm_type);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updating updated_at on the main tables
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON requirements 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_cases_updated_at BEFORE UPDATE ON test_cases 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for easy traceability matrix reporting
CREATE OR REPLACE VIEW traceability_matrix AS
SELECT 
    tl.id,
    tl.source_type,
    tl.source_id,
    tl.source_alm_type,
    tl.source_external_id,
    tl.target_type,
    tl.target_id,
    tl.target_alm_type,
    tl.target_external_id,
    tl.relationship_type,
    tl.confidence_score,
    tl.description,
    tl.status,
    tl.created_at,
    tl.created_by,
    
    -- Source item details (when available)
    CASE 
        WHEN tl.source_type = 'session' THEN s.name
        WHEN tl.source_type = 'requirement' THEN r.title
        WHEN tl.source_type = 'test_case' THEN tc.title
    END as source_title,
    
    -- Target item details (when available)
    CASE 
        WHEN tl.target_type = 'session' THEN s2.name
        WHEN tl.target_type = 'requirement' THEN r2.title
        WHEN tl.target_type = 'test_case' THEN tc2.title
    END as target_title

FROM traceability_links tl
LEFT JOIN sessions s ON tl.source_type = 'session' AND tl.source_id::uuid = s.id
LEFT JOIN requirements r ON tl.source_type = 'requirement' AND tl.source_id::uuid = r.id
LEFT JOIN test_cases tc ON tl.source_type = 'test_case' AND tl.source_id::uuid = tc.id
LEFT JOIN sessions s2 ON tl.target_type = 'session' AND tl.target_id::uuid = s2.id
LEFT JOIN requirements r2 ON tl.target_type = 'requirement' AND tl.target_id::uuid = r2.id
LEFT JOIN test_cases tc2 ON tl.target_type = 'test_case' AND tl.target_id::uuid = tc2.id;

-- Create helper function to add traceability links
CREATE OR REPLACE FUNCTION add_traceability_link(
    p_source_type VARCHAR(50),
    p_source_id VARCHAR(255),
    p_source_alm_type alm_platform_type,
    p_source_external_id VARCHAR(255),
    p_target_type VARCHAR(50),
    p_target_id VARCHAR(255),
    p_target_alm_type alm_platform_type,
    p_target_external_id VARCHAR(255),
    p_relationship_type VARCHAR(50),
    p_confidence_score DECIMAL(3,2) DEFAULT 1.0,
    p_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}',
    p_created_by VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_id UUID;
BEGIN
    INSERT INTO traceability_links (
        source_type, source_id, source_alm_type, source_external_id,
        target_type, target_id, target_alm_type, target_external_id,
        relationship_type, confidence_score, description, metadata, created_by
    ) VALUES (
        p_source_type, p_source_id, p_source_alm_type, p_source_external_id,
        p_target_type, p_target_id, p_target_alm_type, p_target_external_id,
        p_relationship_type, p_confidence_score, p_description, p_metadata, p_created_by
    )
    ON CONFLICT (source_type, source_id, target_type, target_id, relationship_type) 
    DO UPDATE SET
        confidence_score = EXCLUDED.confidence_score,
        description = EXCLUDED.description,
        metadata = EXCLUDED.metadata,
        status = 'active'
    RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Create function to get traceability links for an item
CREATE OR REPLACE FUNCTION get_traceability_links(
    p_item_type VARCHAR(50),
    p_item_id VARCHAR(255),
    p_direction VARCHAR(10) DEFAULT 'both' -- 'source', 'target', 'both'
)
RETURNS TABLE (
    link_id UUID,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    source_alm_type alm_platform_type,
    source_external_id VARCHAR(255),
    source_title TEXT,
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    target_alm_type alm_platform_type,
    target_external_id VARCHAR(255),
    target_title TEXT,
    relationship_type VARCHAR(50),
    confidence_score DECIMAL(3,2),
    description TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tm.id,
        tm.source_type,
        tm.source_id,
        tm.source_alm_type,
        tm.source_external_id,
        tm.source_title,
        tm.target_type,
        tm.target_id,
        tm.target_alm_type,
        tm.target_external_id,
        tm.target_title,
        tm.relationship_type,
        tm.confidence_score,
        tm.description,
        tm.status,
        tm.created_at
    FROM traceability_matrix tm
    WHERE 
        (p_direction IN ('source', 'both') AND tm.source_type = p_item_type AND tm.source_id = p_item_id)
        OR 
        (p_direction IN ('target', 'both') AND tm.target_type = p_item_type AND tm.target_id = p_item_id)
    AND tm.status = 'active'
    ORDER BY tm.created_at DESC;
END;
$$ LANGUAGE plpgsql;