import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Alert, StatusBar } from 'react-native';
import { Icon } from 'react-native-elements';
import { Audio } from 'expo-av';

export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  
  const recording = useRef(null);

  useEffect(() => {
    // Request audio permissions
    requestAudioPermissions();
    

  }, []);

  const requestAudioPermissions = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission needed', 'Audio recording permission is required for the date feature');
      }
    } catch (error) {
      console.error('Error requesting audio permissions:', error);
    }
  };



  const startRecording = async () => {
    try {
      setIsRecording(true);
      
      // Configure audio recording
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      recording.current = newRecording;
      
      console.log('🎤 Recording started');
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      setIsRecording(false);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const stopRecording = async () => {
    try {
      if (!recording.current) return;
      
      await recording.current.stopAndUnloadAsync();
      const uri = recording.current.getURI();
      recording.current = null;
      
      setIsRecording(false);
      console.log('🎤 Recording stopped');
      
      return uri;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setIsRecording(false);
      return null;
    }
  };

  const generateRizz = async () => {
    if (!recording.current) {
      Alert.alert('Error', 'No active recording. Please start recording first.');
      return;
    }

    setIsProcessing(true);
    
    try {
      // Stop recording and get the audio file
      const audioUri = await stopRecording();
      if (!audioUri) {
        Alert.alert('Error', 'Failed to get audio recording');
        setIsProcessing(false);
        return;
      }

      // Create form data for API
      const formData = new FormData();
      
      // Get the file extension from the URI
      const fileExtension = audioUri.split('.').pop() || 'wav';
      const mimeType = `audio/${fileExtension}`;
      
      console.log('🎤 Audio file details:', {
        uri: audioUri,
        type: mimeType,
        name: `recording.${fileExtension}`
      });
      
      formData.append('audio_file', {
        uri: audioUri,
        type: mimeType,
        name: `recording.${fileExtension}`
      });

      // Try different ports for the API
      const ports = [8000, 8001, 8002, 8003, 8004];
      const apiHost = '198.96.35.187'; // Your computer's IP address
      let response = null;
      let data = null;

      for (const port of ports) {
        try {
          response = await fetch(`http://${apiHost}:${port}/rizz`, {
            method: 'POST',
            body: formData,
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });
          data = await response.json();
          console.log(`✅ Connected to API on ${apiHost}:${port}`);
          break;
        } catch (error) {
          console.log(`Port ${port} not available:`, error.message);
          continue;
        }
      }

      if (!data) {
        throw new Error('Could not connect to API on any port');
      }
      
      if (data.success) {
        Alert.alert(
          '🎯 Rizz Generated!', 
          `They said: "${data.transcript}"\n\nYour rizz: "${data.rizz}"\n\nCheck your glasses for the spoken response!`,
          [
            { text: 'OK' },
            { text: 'Get Another Rizz', onPress: () => startRecording() }
          ]
        );
      } else {
        Alert.alert('Error', data.message || 'Failed to generate rizz');
      }

    } catch (error) {
      console.error('Error getting rizz:', error);
      Alert.alert('Error', 'Failed to connect to RizzBot API. Make sure the server is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleMainButtonPress = () => {
    if (isRecording) {
      generateRizz();
    } else {
      startRecording();
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#f8f9fa" />
      
      <View style={styles.header}>
        <Text style={styles.title}>Date Assistant</Text>
        <Text style={styles.subtitle}>Know what to say on a date</Text>
      </View>



      {/* Main Date Button */}
      <View style={styles.mainButtonContainer}>
        <TouchableOpacity
          style={[
            styles.mainButton,
            isRecording && styles.recordingButton,
            isProcessing && styles.processingButton
          ]}
          onPress={handleMainButtonPress}
          disabled={isProcessing}
        >
          <Icon
            name={isRecording ? 'stop' : 'mic'}
            type="material"
            color="#fff"
            size={48}
          />
          <Text style={styles.mainButtonText}>
            {isProcessing ? 'Processing...' : 
             isRecording ? 'Generate Rizz!' : 'Start Date'}
          </Text>
        </TouchableOpacity>

        {isRecording && (
          <Text style={styles.recordingStatus}>
            🎤 Recording... Tap "Generate Rizz!" when you need help
          </Text>
        )}

        {!isRecording && !isProcessing && (
          <Text style={styles.instructions}>
            Tap to start recording your date conversation
          </Text>
        )}
      </View>

      {/* Status Info */}
      <View style={styles.statusContainer}>
        <Text style={styles.statusTitle}>How it works:</Text>
        <Text style={styles.statusText}>1. Tap "Start Date" to begin recording</Text>
        <Text style={styles.statusText}>2. Have your conversation naturally</Text>
        <Text style={styles.statusText}>3. Tap "Generate Rizz!" when you need help</Text>
        <Text style={styles.statusText}>4. Listen to the response through your glasses</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 18,
    color: '#666',
    textAlign: 'center',
  },

  mainButtonContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 30,
  },
  mainButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#007AFF',
    paddingVertical: 30,
    paddingHorizontal: 40,
    borderRadius: 50,
    minWidth: 200,
    minHeight: 200,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  recordingButton: {
    backgroundColor: '#FF3B30',
  },
  processingButton: {
    backgroundColor: '#FF9500',
  },
  mainButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 15,
    textAlign: 'center',
  },
  recordingStatus: {
    fontSize: 16,
    color: '#FF3B30',
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: 20,
    paddingHorizontal: 20,
  },
  instructions: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 20,
    paddingHorizontal: 20,
  },
  statusContainer: {
    backgroundColor: '#fff',
    padding: 20,
    margin: 15,
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
  statusTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
    textAlign: 'center',
  },
  statusText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
    textAlign: 'center',
  },
});
