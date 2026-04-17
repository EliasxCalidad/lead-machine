-- Lead Machine Schema
-- Run this in your Supabase SQL editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Leads: one row per company found on Google Maps
CREATE TABLE leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_name TEXT NOT NULL,
  website_url TEXT,
  email TEXT,
  phone TEXT,
  address TEXT,
  city TEXT DEFAULT 'Stockholm',
  category TEXT,
  google_place_id TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'pending'
  -- pending → analyzing → analyzed → generating → email_ready → sent → bounced → opened → replied
);

-- Website analyses: one row per analyzed lead
CREATE TABLE analyses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  pagespeed_mobile INTEGER,
  pagespeed_desktop INTEGER,
  has_ssl BOOLEAN DEFAULT false,
  has_contact_form BOOLEAN DEFAULT false,
  has_google_analytics BOOLEAN DEFAULT false,
  has_social_links BOOLEAN DEFAULT false,
  has_blog BOOLEAN DEFAULT false,
  has_google_maps_embed BOOLEAN DEFAULT false,
  meta_title TEXT,
  meta_description TEXT,
  copyright_year INTEGER,
  cms_detected TEXT,
  issues JSONB DEFAULT '[]',
  recommended_package TEXT,
  ai_analysis TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Emails: generated + sent emails
CREATE TABLE emails (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  subject TEXT,
  body_html TEXT,
  body_text TEXT,
  to_email TEXT,
  sendgrid_message_id TEXT,
  status TEXT DEFAULT 'draft',
  -- draft → sent → bounced → opened → clicked → replied
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline runs: log of each automated run
CREATE TABLE pipeline_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  scraped_count INTEGER DEFAULT 0,
  analyzed_count INTEGER DEFAULT 0,
  emails_sent_count INTEGER DEFAULT 0,
  errors_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'running',
  log TEXT
);

-- Useful views for the dashboard
CREATE VIEW dashboard_stats AS
SELECT
  COUNT(*) FILTER (WHERE status != 'pending') AS total_leads,
  COUNT(*) FILTER (WHERE status = 'sent' OR status = 'opened' OR status = 'clicked' OR status = 'replied') AS emails_sent,
  COUNT(*) FILTER (WHERE status = 'opened' OR status = 'clicked' OR status = 'replied') AS emails_opened,
  COUNT(*) FILTER (WHERE status = 'replied') AS emails_replied,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE status = 'opened' OR status = 'replied') /
    NULLIF(COUNT(*) FILTER (WHERE status = 'sent' OR status = 'opened' OR status = 'replied'), 0), 1
  ) AS open_rate_pct,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE status = 'replied') /
    NULLIF(COUNT(*) FILTER (WHERE status = 'sent' OR status = 'opened' OR status = 'replied'), 0), 1
  ) AS reply_rate_pct
FROM leads;

-- Indexes
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX idx_emails_lead_id ON emails(lead_id);
CREATE INDEX idx_analyses_lead_id ON analyses(lead_id);
