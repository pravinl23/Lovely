"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Calendar, MapPin, Clock, Plus } from "lucide-react"

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
}

interface ContactDetailProps {
  contactId: string
  contacts: Contact[]
  onBack: () => void
}

// Mock detailed contact data
const mockContactDetails: Record<string, any> = {
  "1": {
    name: "AVA",
    image: "/images/ava-new.png", // Updated image path
    facts: [
      "⚽ Plays soccer regularly and enjoys both the competitive and team aspects of the game",
      "✍️ Enjoys writing as a creative outlet, with a focus on personal reflections and short-form pieces",
      "📸 Has a strong interest in photography, especially in capturing everyday nature and urban scenes",
    ],
  },
  "2": {
    name: "SOPHIA",
    image: "/images/sophia-closeup.jpg", // Use actual image
    facts: [
      "🎵 New Jeans superfan who knows all their songs and choreography",
      "⛷️ Loves skiing and goes on winter trips whenever possible",
      "📷 Photography enthusiast who captures moments during travels",
    ],
  },
  "3": {
    name: "ANDREA CALZONI",
    image: "/images/girl-mirror-selfie.png", // Use actual image
    facts: [
      "⚽ Plays soccer regularly and enjoys both the competitive and team aspects of the game",
      "✍️ Enjoys writing as a creative outlet, with a focus on personal reflections and short-form pieces",
      "📸 Has a strong interest in photography, especially in capturing everyday nature and urban scenes",
    ],
  },
}

export default function ContactDetail({ contactId, contacts, onBack }: ContactDetailProps) {
  const contact = mockContactDetails[contactId as keyof typeof mockContactDetails]
  const contactData = contacts.find((c) => c.id === contactId)

  if (!contact) return null

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  const addToCalendar = () => {
    if (contactData?.dateInfo) {
      const { location, date, time } = contactData.dateInfo
      const startDate = new Date(`${date} ${time}`)
      const endDate = new Date(startDate.getTime() + 2 * 60 * 60 * 1000) // 2 hours later

      const googleCalendarUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=Date with ${contact.name}&dates=${startDate.toISOString().replace(/[-:]/g, "").split(".")[0]}Z/${endDate.toISOString().replace(/[-:]/g, "").split(".")[0]}Z&details=Date with ${contact.name}&location=${encodeURIComponent(location)}`

      window.open(googleCalendarUrl, "_blank")
    }
  }

  return (
    <div className="min-h-screen bg-pink-50 animate-fade-in">
      {/* Header */}
      <div className="flex items-center p-4 pt-12">
        <Button variant="ghost" size="icon" onClick={onBack} className="mr-3 hover:bg-gray-100 transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1
          className="text-4xl font-black text-black"
          style={{ fontFamily: "system-ui, -apple-system, sans-serif", letterSpacing: "-0.02em" }}
        >
          Lovely
        </h1>
      </div>

      {/* Profile Card */}
      <div className="px-4">
        <Card className="overflow-hidden rounded-3xl border-0 shadow-lg animate-slide-up">
          <div className="flex h-full">
            {" "}
            {/* Flex container for side-by-side layout */}
            {/* About Section (Left Column) */}
            <CardContent className="p-6 flex-1 flex flex-col">
              <h3 className="text-gray-500 text-lg font-medium mb-4">About</h3>
              <div className="space-y-3 mb-6 flex-1">
                {contact.facts.map((fact: string, index: number) => (
                  <div
                    key={index}
                    className="bg-gray-50 rounded-2xl p-4 border border-gray-100 transform transition-all duration-300 hover:shadow-md hover:scale-[1.02]"
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <p className="text-gray-700 text-sm leading-relaxed">{fact}</p>
                  </div>
                ))}
              </div>

              {/* Date Planning Section */}
              {contactData?.hasDate && contactData.dateInfo && (
                <div className="border-t border-gray-100 pt-6">
                  <h3 className="text-gray-500 text-lg font-medium mb-4 flex items-center">
                    <Calendar className="h-5 w-5 mr-2 text-pink-500" />
                    Date Plan
                  </h3>

                  <Card className="bg-pink-500 border border-pink-100 rounded-2xl overflow-hidden">
                    <CardContent className="p-6">
                      <div className="flex flex-row flex-wrap justify-between gap-2">
                        {/* Location */}
                        <div className="bg-pink-300 rounded-2xl p-2 flex-1 min-w-[100px]">
                          <div className="flex items-center mb-1">
                            <MapPin className="h-5 w-5 mr-1 text-white" />
                            <span className="font-semibold text-sm text-white">Location</span>
                          </div>
                          <span className="text-base text-white">{contactData.dateInfo.location}</span>
                        </div>

                        {/* Date */}
                        <div className="bg-pink-300 rounded-2xl p-2 flex-1 min-w-[100px]">
                          <div className="flex items-center mb-1">
                            <Calendar className="h-5 w-5 mr-1 text-white" />
                            <span className="font-semibold text-sm text-white">Date</span>
                          </div>
                          <span className="text-base text-white">{formatDate(contactData.dateInfo.date)}</span>
                        </div>

                        {/* Time */}
                        <div className="bg-pink-300 rounded-2xl p-2 flex-1 min-w-[100px]">
                          <div className="flex items-center mb-1">
                            <Clock className="h-5 w-5 mr-1 text-white" />
                            <span className="font-semibold text-sm text-white">Time</span>
                          </div>
                          <span className="text-base text-white">{contactData.dateInfo.time}</span>
                        </div>

                        {/* Add to Calendar Button */}
                        <Button
                          onClick={addToCalendar}
                          className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-medium py-3 rounded-xl transform transition-all duration-300 hover:scale-105 hover:shadow-lg flex items-center justify-center mt-6 col-span-2"
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add to Calendar
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </CardContent>
            {/* Image (Right Column) */}
            <div className="relative w-1/2 flex-shrink-0 rounded-full overflow-hidden">
              <img
                src={contact.image || "/placeholder.svg"}
                alt={contact.name}
                className="w-full h-full object-cover"
              />
              {/* Gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/10 via-transparent to-transparent" />
            </div>
          </div>
        </Card>
      </div>

      <style jsx>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(30px);
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
        .animate-slide-up {
          animation: slideUp 0.6s ease-out;
        }
      `}</style>
    </div>
  )
}
