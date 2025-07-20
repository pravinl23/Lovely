"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Bell,
  MoreHorizontal,
  Download,
  ArrowRight,
  Heart,
  Eye,
  UserMinus,
  Calendar,
  MapPin,
  Clock,
  Plus,
} from "lucide-react"
import ContactDetail from "@/components/contact-detail"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

interface Contact {
  id: string
  name: string
  facts: string[]
  image: string
  hasDate?: boolean
  dateInfo?: {
    location: string
    date: string
    time: string
  }
  isNewDate?: boolean // Added for new date notification
  isFavorite?: boolean // Added for favorites feature
}

// Mock data with real images - blonde girl first
const initialContacts: Contact[] = [
  {
    id: "1",
    name: "AVA",
    facts: ["Very friendly", "Listens to Taylor Swift", "CS major"],
    image: "/images/ava-new.png", // Updated image path
    hasDate: true,
    dateInfo: {
      location: "Central Park Cafe",
      date: "2024-01-25",
      time: "7:00 PM",
    },
    isNewDate: true, // Ava has a new date
    isFavorite: false,
  },
  {
    id: "2",
    name: "SOPHIA",
    facts: ["New Jeans superfan", "Loves skiing", "Plays tennis"],
    image: "/images/sophia-closeup.jpg",
    isFavorite: false,
  },
  {
    id: "3",
    name: "ANDREA",
    facts: ["Plays soccer regularly", "Enjoys writing", "Photography lover"],
    image: "/images/girl-mirror-selfie.png",
    hasDate: true,
    dateInfo: {
      location: "Art Museum Downtown",
      date: "2024-01-28",
      time: "2:30 PM",
    },
    isFavorite: false,
  },
]

export default function HomePage() {
  const [currentScreen, setCurrentScreen] = useState<
    "splash" | "phone" | "loading" | "landing" | "connecting" | "contacts" | "detail"
  >("splash")
  const [selectedContact, setSelectedContact] = useState<string | null>(null)
  const [phoneNumber, setPhoneNumber] = useState("")
  const [messageIndex, setMessageIndex] = useState(0)
  const [hasNewNotification, setHasNewNotification] = useState(true) // State for notification dot
  const [contacts, setContacts] = useState<Contact[]>(initialContacts) // State for contacts
  const [showCalendarConnectMessage, setShowCalendarConnectMessage] = useState(false)

  const flirtyMessages = [
    "Sprinkling some magic dust... ✨",
    "Teaching our AI to be charming... 😉",
    "Warming up the conversation starters... 🔥",
    "Making sure you look irresistible...💋",
    "Cupid is loading his best arrows... 💘",
  ]

  // Format phone display with underscores replaced by numbers
  const getPhoneDisplay = () => {
    const template = "___-___-____"
    let result = ""
    let numberIndex = 0

    for (let i = 0; i < template.length; i++) {
      if (template[i] === "_") {
        if (numberIndex < phoneNumber.length) {
          result += phoneNumber[numberIndex]
          numberIndex++
        } else {
          result += "_"
        }
      } else {
        result += template[i]
      }
    }
    return result
  }

  // Handle keyboard input for phone screen
  useEffect(() => {
    if (currentScreen === "phone") {
      const handleKeyPress = (e: KeyboardEvent) => {
        e.preventDefault()

        if (e.key >= "0" && e.key <= "9" && phoneNumber.length < 10) {
          setPhoneNumber((prev) => prev + e.key)
        } else if (e.key === "Backspace" && phoneNumber.length > 0) {
          setPhoneNumber((prev) => prev.slice(0, -1))
        } else if (e.key === "Enter" && phoneNumber.length === 10) {
          setCurrentScreen("loading")
        }
      }

      window.addEventListener("keydown", handleKeyPress)
      return () => window.removeEventListener("keydown", handleKeyPress)
    }
  }, [currentScreen, phoneNumber])

  // Loading screen effect
  useEffect(() => {
    if (currentScreen === "loading") {
      const timer = setTimeout(() => {
        setCurrentScreen("landing")
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [currentScreen])

  // Connecting screen effect
  useEffect(() => {
    if (currentScreen === "connecting") {
      const timer = setTimeout(() => {
        setCurrentScreen("contacts")
      }, 2500)
      return () => clearTimeout(timer)
    }
  }, [currentScreen])

  // Flirty messages effect - slower rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % flirtyMessages.length)
    }, 1400) // Changed from 800ms to 1400ms (1.75x slower)
    return () => clearInterval(interval)
  }, [])

  // Handle "Add to Calendar" message display
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (showCalendarConnectMessage) {
      timer = setTimeout(() => {
        setShowCalendarConnectMessage(false)
      }, 3000) // Message disappears after 3 seconds
    }
    return () => clearTimeout(timer)
  }, [showCalendarConnectMessage])

  const handleRemoveContact = (id: string) => {
    setContacts(contacts.filter((contact) => contact.id !== id))
  }

  const handleToggleFavorite = (id: string) => {
    setContacts(
      contacts.map((contact) => (contact.id === id ? { ...contact, isFavorite: !contact.isFavorite } : contact)),
    )
  }

  const handleAddToCalendarClick = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click from triggering
    setShowCalendarConnectMessage(true)
  }

  // Splash Screen with real cupid image
  if (currentScreen === "splash") {
    return (
      <div className="min-h-screen bg-pink-50 flex flex-col items-center justify-center px-6 relative overflow-hidden">
        {/* Real cupid illustration - blends perfectly with background */}
        <div className="mb-12 relative w-full h-64 flex items-center justify-center">
          {/* Cupid positioned closer to center */}
          <div className="absolute left-20 top-1/2 transform -translate-y-1/2 animate-cupid-float">
            <img src="/images/cupid-final.png" alt="Cupid illustration" className="w-48 h-48 object-contain" />
          </div>

          {/* Arrow positioned closer to cupid */}
          <div className="absolute right-20 top-8 animate-arrow-fly">
            <img
              src="/images/cupid-arrow.png"
              alt="Cupid's arrow"
              className="w-24 h-6 object-contain transform rotate-12"
            />
          </div>
        </div>

        {/* Lovely branding - consistent font */}
        <h1
          className="text-6xl font-black text-black mb-8 animate-fade-in-up"
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            letterSpacing: "-0.02em",
          }}
        >
          Lovely
        </h1>

        {/* Tagline */}
        <div className="text-center mb-16 animate-fade-in-up-delay">
          <h2 className="text-3xl font-bold text-gray-800 leading-tight">
            We flirt. You just
            <br />
            show up cute.
          </h2>
        </div>

        {/* WhatsApp Login Button with enhanced expand effect */}
        <Button
          className="w-full max-w-sm bg-green-500 hover:bg-green-600 text-white font-medium py-4 rounded-xl mb-6 flex items-center justify-center transform transition-all duration-300 hover:scale-125 hover:shadow-2xl animate-fade-in-up-delay-2 hover:rounded-2xl"
          onClick={() => setCurrentScreen("phone")}
        >
          <svg
            className="w-6 h-6 mr-3 transition-transform duration-300 hover:scale-110"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
          </svg>
          <span className="transition-all duration-300 hover:tracking-wider">Login with WhatsApp</span>
        </Button>

        {/* Sign up link */}
        <p className="text-gray-600 text-center animate-fade-in-up-delay-3">
          Don't have an account?{" "}
          <button className="text-pink-500 font-medium hover:text-pink-600 transition-colors">Sign Up</button>
        </p>

        <style jsx>{`
          @keyframes cupidFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-15px); }
          }
          @keyframes fadeInUp {
            from {
              opacity: 0;
              transform: translateY(30px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
          @keyframes arrowFly {
            0% { 
              transform: translateY(-50%) translateX(0px);
              opacity: 0.8;
            }
            50% { 
              transform: translateY(-50%) translateX(20px);
              opacity: 1;
            }
            100% { 
              transform: translateY(-50%) translateX(0px);
              opacity: 0.8;
            }
          }
          .animate-cupid-float {
            animation: cupidFloat 4s ease-in-out infinite;
          }
          .animate-fade-in-up {
            animation: fadeInUp 1s ease-out;
          }
          .animate-fade-in-up-delay {
            animation: fadeInUp 1s ease-out 0.3s both;
          }
          .animate-fade-in-up-delay-2 {
            animation: fadeInUp 1s ease-out 0.6s both;
          }
          .animate-fade-in-up-delay-3 {
            animation: fadeInUp 1s ease-out 0.9s both;
          }
          .animate-arrow-fly {
            animation: arrowFly 3s ease-in-out infinite;
          }
        `}</style>
      </div>
    )
  }

  // Phone Input Screen - fixed with proper underscore replacement
  if (currentScreen === "phone") {
    return (
      <div className="min-h-screen bg-pink-50 flex flex-col items-center justify-center px-6 animate-fade-in">
        {/* Lovely branding - consistent font */}
        <h1
          className="text-5xl font-black text-black mb-16"
          style={{ fontFamily: "system-ui, -apple-system, sans-serif", letterSpacing: "-0.02em" }}
        >
          Lovely
        </h1>

        {/* Instructions */}
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-gray-800 leading-tight">
            Just type in your
            <br />
            phone number...
          </h2>
        </div>

        {/* Phone display - only visible formatted text, no border */}
        <div className="w-full max-w-sm mb-8">
          <div className="text-center text-4xl py-4 font-mono tracking-wider text-gray-800 min-h-[60px] flex items-center justify-center">
            {getPhoneDisplay()}
          </div>
          {/* Invisible input to capture focus */}
          <input
            type="text"
            className="absolute opacity-0 pointer-events-none"
            autoFocus
            value=""
            onChange={() => {}} // Controlled by keyboard events
          />
        </div>

        {/* Sign Up button - moved above WhatsApp */}
        <Button
          variant="ghost"
          className="bg-purple-100 text-purple-600 px-8 py-3 rounded-full hover:bg-purple-200 transition-all duration-300 hover:scale-105 mb-6"
          disabled={phoneNumber.length !== 10}
          onClick={() => setCurrentScreen("loading")}
        >
          Log In
        </Button>

        {/* WhatsApp logo - moved below */}
        <div className="flex items-center justify-center mt-8">
          <Button variant="ghost" className="flex items-center text-green-600 hover:text-green-700 transition-colors">
            <svg className="w-6 h-6 mr-2" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
            </svg>
          </Button>
        </div>
      </div>
    )
  }

  // Loading Screen - cupid themed with flirty messages
  if (currentScreen === "loading") {
    return (
      <div className="min-h-screen bg-pink-50 flex flex-col items-center justify-center px-6">
        {/* Animated cupid */}
        <div className="mb-8 relative">
          <div className="w-24 h-24 bg-pink-200 rounded-full flex items-center justify-center animate-pulse">
            <svg className="w-12 h-12 text-pink-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>
          {/* Floating hearts */}
          <div className="absolute -top-2 -right-2 text-pink-400 animate-bounce">💕</div>
          <div className="absolute -bottom-2 -left-2 text-purple-400 animate-bounce delay-300">💖</div>
        </div>

        {/* Loading text with rotating flirty messages */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Getting you ready to charm...</h2>
          <p className="text-gray-600 animate-pulse min-h-[24px]">{flirtyMessages[messageIndex]}</p>
        </div>

        {/* Progress dots */}
        <div className="flex space-x-2 mt-8">
          <div className="w-3 h-3 bg-pink-400 rounded-full animate-bounce"></div>
          <div className="w-3 h-3 bg-purple-400 rounded-full animate-bounce delay-100"></div>
          <div className="w-3 h-3 bg-pink-400 rounded-full animate-bounce delay-200"></div>
        </div>
      </div>
    )
  }

  // Landing Page
  if (currentScreen === "landing") {
    return (
      <div className="min-h-screen bg-pink-50 flex flex-col items-center justify-center px-6 animate-fade-in">
        {/* Lovely branding - consistent font */}
        <h1
          className="text-6xl font-black text-black mb-8"
          style={{ fontFamily: "system-ui, -apple-system, sans-serif", letterSpacing: "-0.02em" }}
        >
          Lovely
        </h1>

        {/* Welcome message */}
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Welcome to Lovely!</h2>
          <p className="text-gray-600 text-lg">Choose how you'd like to continue</p>
        </div>

        {/* Action buttons */}
        <div className="w-full max-w-sm space-y-4">
          <Button
            className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-4 rounded-xl transform transition-all duration-300 hover:scale-105 hover:shadow-lg flex items-center justify-center"
            onClick={() => setCurrentScreen("connecting")}
          >
            Continue to Web App
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>

          <Button
            variant="outline"
            className="w-full border-2 border-gray-300 hover:border-gray-400 text-gray-700 font-medium py-4 rounded-xl transform transition-all duration-300 hover:scale-105 hover:shadow-lg flex items-center justify-center bg-transparent"
          >
            <Download className="mr-2 h-5 w-5" />
            Download Mobile App
          </Button>
        </div>

        {/* Features preview */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500 mb-4">
            ✨ AI-powered conversations • 💬 WhatsApp integration • 📅 Smart date planning
          </p>
        </div>
      </div>
    )
  }

  // Connecting Screen - new loading screen
  if (currentScreen === "connecting") {
    return (
      <div className="min-h-screen bg-pink-50 flex flex-col items-center justify-center px-6">
        {/* Animated connection icon */}
        <div className="mb-8 relative">
          <div className="w-24 h-24 bg-purple-200 rounded-full flex items-center justify-center animate-pulse">
            <svg className="w-12 h-12 text-purple-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>
          {/* Connection waves */}
          <div className="absolute -top-4 -right-4 text-purple-400 animate-ping">📱</div>
          <div className="absolute -bottom-4 -left-4 text-pink-400 animate-ping delay-300">💬</div>
        </div>

        {/* Loading text */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Connecting to contacts...</h2>
          <p className="text-gray-600 animate-pulse">Almost there!</p>
        </div>

        {/* Progress dots */}
        <div className="flex space-x-2 mt-8">
          <div className="w-3 h-3 bg-purple-400 rounded-full animate-bounce"></div>
          <div className="w-3 h-3 bg-pink-400 rounded-full animate-bounce delay-100"></div>
          <div className="w-3 h-3 bg-purple-400 rounded-full animate-bounce delay-200"></div>
        </div>
      </div>
    )
  }

  // Contact Detail Screen
  if (currentScreen === "detail" && selectedContact) {
    return (
      <ContactDetail
        contactId={selectedContact}
        contacts={contacts} // Pass the stateful contacts
        onBack={() => {
          setCurrentScreen("contacts")
          setSelectedContact(null)
        }}
      />
    )
  }

  // Contacts Screen - Horizontal Layout matching the reference image
  return (
    <div className="min-h-screen bg-pink-50 animate-fade-in">
      {/* Notification Banner */}
      {hasNewNotification && (
        <div className="bg-gradient-to-r from-pink-400 to-purple-500 text-white text-center py-3 text-lg font-semibold">
          1 new date has been secured!
        </div>
      )}
      {showCalendarConnectMessage && (
        <div className="bg-yellow-400 text-white text-center py-2 text-sm font-medium">
          Must connect calendar through WhatsApp/Meta
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-6 pt-12">
        <h1 className="text-4xl font-bold text-purple-900">Contacts</h1>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full bg-gray-100 hover:bg-gray-200 transition-all duration-300 hover:scale-110 relative"
        >
          <Bell className="h-5 w-5" />
          {hasNewNotification && (
            <span className="absolute top-1 right-1 block h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
          )}
        </Button>
      </div>

      {/* Contact Cards - Horizontal Layout */}
      <div className="px-6 space-y-6">
        {contacts.map((contact, index) => (
          <div
            key={contact.id}
            className="flex items-stretch space-x-4 h-64 cursor-pointer transform transition-all duration-300 hover:scale-[1.02]"
            onClick={() => {
              setSelectedContact(contact.id)
              setCurrentScreen("detail")
            }}
            style={{
              animation: `slideInUp 0.6s ease-out ${index * 0.1}s both`,
            }}
          >
            {/* Profile Image */}
            <div className="relative w-64 h-full rounded-3xl overflow-hidden flex-shrink-0 group">
              <img
                src={contact.image || "/placeholder.svg"}
                alt={contact.name}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110 rounded-full"
              />

              {/* Three dots menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute bottom-4 right-4 bg-black/30 backdrop-blur-sm rounded-full text-white hover:bg-black/40 transition-all duration-300 hover:scale-110"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-48 bg-white/95 backdrop-blur-sm border border-gray-200 rounded-xl shadow-lg">
                  <DropdownMenuItem
                    className="flex items-center space-x-2 hover:bg-gray-50 rounded-lg transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedContact(contact.id)
                      setCurrentScreen("detail")
                    }}
                  >
                    <Eye className="h-4 w-4 text-blue-500" />
                    <span>See More Details</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="flex items-center space-x-2 hover:bg-gray-50 rounded-lg transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleToggleFavorite(contact.id)
                    }}
                  >
                    <Heart className="h-4 w-4 text-pink-500" />
                    <span>{contact.isFavorite ? "Unfavorite" : "Add to Favorites"}</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="flex items-center space-x-2 hover:bg-gray-50 rounded-lg transition-colors text-red-600"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveContact(contact.id)
                    }}
                  >
                    <UserMinus className="h-4 w-4" />
                    <span>Remove Contact</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Info Panel (Notes) */}
            <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm flex flex-col h-full flex-[2]">
              {/* Name Badge and New Date/Favorite */}
              <div className="flex flex-col items-center justify-center mb-6">
                <div className="flex items-center">
                  <div className="inline-block bg-gradient-to-r from-pink-500 to-purple-600 text-white px-6 py-3 rounded-full">
                    <span className="font-bold text-xl">{contact.name}</span>
                  </div>
                  {contact.isFavorite && <Heart className="h-5 w-5 text-pink-500 ml-2" fill="currentColor" />}
                </div>
                {contact.isNewDate && (
                  <div className="mt-2 relative">
                    <div className="absolute inset-0 border-2 border-dashed border-purple-600 rounded-full animate-pulse" />
                    <span className="relative bg-purple-100 text-purple-700 font-bold text-sm px-3 py-1 rounded-full transform -rotate-6">
                      New date!
                    </span>
                  </div>
                )}
              </div>

              {/* Facts */}
              <div className="space-y-3 flex-1">
                {contact.facts.map((fact, factIndex) => (
                  <div key={factIndex} className="flex items-center text-gray-800">
                    <div className="w-2 h-2 bg-gray-800 rounded-full mr-3 flex-shrink-0" />
                    <span className="text-lg font-medium">{fact}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Date Planned Box / No Date Planned Box */}
            {contact.hasDate && contact.dateInfo ? (
              <div className="flex-[1.2] bg-pink-500 rounded-3xl p-6 shadow-lg flex-shrink-0 flex flex-col h-full">
                <div className="text-center mb-4">
                  <div className="bg-pink-400 rounded-full px-4 py-2 inline-block mb-4">
                    <span className="text-white font-bold text-lg flex items-center justify-center">
                      <Calendar className="h-5 w-5 mr-2" />
                      Date Planned
                    </span>
                  </div>
                </div>

                <div className="flex flex-row justify-between gap-2 text-white flex-1">
                  {/* Location */}
                  <div className="bg-pink-300 rounded-2xl p-2 w-1/3 flex flex-col items-center text-center">
                    <div className="flex items-center mb-1">
                      <MapPin className="h-5 w-5 mr-1 text-white" />
                      <span className="font-semibold text-sm">Location</span>
                    </div>
                    <span className="text-base">{contact.dateInfo.location}</span>
                  </div>

                  {/* Date */}
                  <div className="bg-pink-300 rounded-2xl p-2 w-1/3 flex flex-col items-center text-center">
                    <div className="flex items-center mb-1">
                      <Calendar className="h-5 w-5 mr-1 text-white" />
                      <span className="font-semibold text-sm">Date</span>
                    </div>
                    <span className="text-base">
                      {new Date(contact.dateInfo.date).toLocaleDateString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </div>

                  {/* Time */}
                  <div className="bg-pink-300 rounded-2xl p-2 w-1/3 flex flex-col items-center text-center">
                    <div className="flex items-center mb-1">
                      <Clock className="h-5 w-5 mr-1 text-white" />
                      <span className="font-semibold text-sm">Time</span>
                    </div>
                    <span className="text-base">{contact.dateInfo.time}</span>
                  </div>
                </div>
                {/* Add to Calendar Button */}
                <Button
                  onClick={handleAddToCalendarClick}
                  className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-3 rounded-xl transform transition-all duration-300 hover:scale-105 hover:shadow-lg flex items-center justify-center mt-6"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add to Calendar
                </Button>
              </div>
            ) : (
              <div className="flex-[1.2] bg-pink-100 rounded-3xl p-6 shadow-sm flex-shrink-0 flex flex-col h-full text-gray-500">
                <div className="flex-1 flex flex-col items-center justify-center">
                  <Calendar className="h-12 w-12 mb-4 text-pink-300" />
                  <p className="text-lg font-semibold text-center">No date has been planned yet.</p>
                  <p className="text-sm text-center mt-2">Check back later!</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes slideInUp {
          from {
            opacity: 0;
            transform: translateY(50px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .animate-fade-in {
          animation: fadeIn 0.5s ease-out;
        }
      `}</style>
    </div>
  )
}
