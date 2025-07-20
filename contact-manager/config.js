// Configuration file for Contact Manager App
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '@env';

export const CONFIG = {
  // Supabase Configuration from environment variables
  SUPABASE: {
    URL: SUPABASE_URL || 'your_supabase_url_here',
    ANON_KEY: SUPABASE_ANON_KEY || 'your_supabase_anon_key_here'
  },
  
  // Contact Mapping (hardcoded for demo)
  CONTACT_MAPPING: {
    '647': { name: 'Bob', knowledgeFile: 'bob.json' },
    '416': { name: 'Isabella', knowledgeFile: 'isabella.json' },
    '289': { name: 'Adam', knowledgeFile: 'adam.json' }
  },
  
  // App Settings
  APP: {
    DEFAULT_SETTINGS_ID: 1,
    MAX_CONTACTS: 100,
    REFRESH_INTERVAL: 30000 // 30 seconds
  },
  
  // UI Configuration
  UI: {
    COLORS: {
      primary: '#007AFF',
      secondary: '#5856D6',
      success: '#34C759',
      warning: '#FF9500',
      danger: '#FF3B30',
      light: '#F2F2F7',
      dark: '#1C1C1E',
      background: '#F8F9FA',
      card: '#FFFFFF',
      text: '#333333',
      textSecondary: '#666666',
      border: '#E0E0E0'
    },
    
    SIZES: {
      padding: 20,
      margin: 15,
      borderRadius: 12,
      iconSize: 24,
      buttonHeight: 44
    }
  }
};

export default CONFIG; 