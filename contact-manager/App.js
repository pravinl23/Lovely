import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, FlatList, TouchableOpacity, Alert, StatusBar } from 'react-native';
import { Icon } from 'react-native-elements';

export default function App() {
  const [contacts, setContacts] = useState([]);
  const [starredContact, setStarredContact] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize with demo contacts
    const demoContacts = [
      {
        id: 647,
        name: 'Bob',
        phone_number: '647',
        knowledge_file: 'bob.json',
        is_whitelisted: false
      },
      {
        id: 416,
        name: 'Isabella',
        phone_number: '416',
        knowledge_file: 'isabella.json',
        is_whitelisted: false
      },
      {
        id: 289,
        name: 'Adam',
        phone_number: '289',
        knowledge_file: 'adam.json',
        is_whitelisted: false
      }
    ];
    
    setContacts(demoContacts);
    setLoading(false);
  }, []);

  const toggleWhitelist = (contactId) => {
    setContacts(prev => prev.map(c => 
      c.id === contactId ? { ...c, is_whitelisted: !c.is_whitelisted } : c
    ));
    
    const contact = contacts.find(c => c.id === contactId);
    const newStatus = !contact.is_whitelisted;
    Alert.alert(
      'Success', 
      `${contact.name} ${newStatus ? 'whitelisted' : 'removed from whitelist'}`
    );
  };

  const toggleStar = (contactId) => {
    const contact = contacts.find(c => c.id === contactId);
    const isCurrentlyStarred = starredContact === contactId;
    
    if (isCurrentlyStarred) {
      setStarredContact(null);
      Alert.alert('Success', 'No active date selected');
    } else {
      setStarredContact(contactId);
      Alert.alert('Success', `${contact.name} is now your active date!`);
    }
  };

  const renderContact = ({ item }) => {
    const isStarred = starredContact === item.id;
    
    return (
      <View style={styles.contactItem}>
        <View style={styles.contactInfo}>
          <Text style={styles.contactName}>{item.name}</Text>
          <Text style={styles.contactPhone}>{item.phone_number}</Text>
          <Text style={styles.knowledgeFile}>Knowledge: {item.knowledge_file}</Text>
        </View>
        
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[
              styles.button,
              item.is_whitelisted ? styles.whitelistedButton : styles.whitelistButton
            ]}
            onPress={() => toggleWhitelist(item.id)}
          >
            <Icon
              name={item.is_whitelisted ? 'check-circle' : 'add-circle-outline'}
              type="material"
              color={item.is_whitelisted ? '#4CAF50' : '#666'}
              size={24}
            />
            <Text style={[
              styles.buttonText,
              item.is_whitelisted ? styles.whitelistedText : styles.whitelistText
            ]}>
              {item.is_whitelisted ? 'Whitelisted' : 'Whitelist'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.button,
              isStarred ? styles.starredButton : styles.starButton
            ]}
            onPress={() => toggleStar(item.id)}
          >
            <Icon
              name={isStarred ? 'star' : 'star-border'}
              type="material"
              color={isStarred ? '#FFD700' : '#666'}
              size={24}
            />
            <Text style={[
              styles.buttonText,
              isStarred ? styles.starredText : styles.starText
            ]}>
              {isStarred ? 'Active Date' : 'Star'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading contacts...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#f8f9fa" />
      
      <View style={styles.header}>
        <Text style={styles.title}>Contact Manager</Text>
        <Text style={styles.subtitle}>Manage your WhatsApp contacts</Text>
      </View>

      {starredContact && (
        <View style={styles.activeDateContainer}>
          <Icon name="star" type="material" color="#FFD700" size={20} />
          <Text style={styles.activeDateText}>
            Active Date: {contacts.find(c => c.id === starredContact)?.name}
          </Text>
        </View>
      )}

      <FlatList
        data={contacts}
        renderItem={renderContact}
        keyExtractor={(item) => item.id.toString()}
        style={styles.list}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
  },
  loadingText: {
    fontSize: 18,
    color: '#666',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  activeDateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF3CD',
    padding: 15,
    margin: 15,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#FFD700',
  },
  activeDateText: {
    marginLeft: 10,
    fontSize: 16,
    fontWeight: '600',
    color: '#856404',
  },
  list: {
    flex: 1,
    paddingHorizontal: 15,
  },
  contactItem: {
    backgroundColor: '#fff',
    padding: 20,
    marginVertical: 8,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  contactInfo: {
    marginBottom: 15,
  },
  contactName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  contactPhone: {
    fontSize: 16,
    color: '#666',
    marginBottom: 5,
  },
  knowledgeFile: {
    fontSize: 14,
    color: '#999',
    fontStyle: 'italic',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
    flex: 0.48,
    justifyContent: 'center',
  },
  whitelistButton: {
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  whitelistedButton: {
    backgroundColor: '#E8F5E8',
    borderWidth: 1,
    borderColor: '#4CAF50',
  },
  starButton: {
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  starredButton: {
    backgroundColor: '#FFF8DC',
    borderWidth: 1,
    borderColor: '#FFD700',
  },
  buttonText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '600',
  },
  whitelistText: {
    color: '#666',
  },
  whitelistedText: {
    color: '#4CAF50',
  },
  starText: {
    color: '#666',
  },
  starredText: {
    color: '#B8860B',
  },
});
