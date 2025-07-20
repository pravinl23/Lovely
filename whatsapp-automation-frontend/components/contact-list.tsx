"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MessageCircle, Clock, Heart } from "lucide-react"

interface Contact {
  id: string
  name: string
  lastMessage: string
  timestamp: string
  status: "new" | "familiar" | "trusted"
  unreadCount: number
  avatar: string
}

// Mock data for demonstration
const mockContacts: Contact[] = [
  {
    id: "1",
    name: "Emma",
    lastMessage: "Hey! How was your day?",
    timestamp: "2 min ago",
    status: "trusted",
    unreadCount: 2,
    avatar: "/placeholder.svg?height=50&width=50",
  },
  {
    id: "2",
    name: "Sofia",
    lastMessage: "Thanks for the recommendation!",
    timestamp: "1 hour ago",
    status: "familiar",
    unreadCount: 0,
    avatar: "/placeholder.svg?height=50&width=50",
  },
  {
    id: "3",
    name: "Maya",
    lastMessage: "Nice to meet you!",
    timestamp: "3 hours ago",
    status: "new",
    unreadCount: 1,
    avatar: "/placeholder.svg?height=50&width=50",
  },
]

export default function ContactList() {
  const [selectedContact, setSelectedContact] = useState<string | null>(null)

  const getStatusColor = (status: Contact["status"]) => {
    switch (status) {
      case "new":
        return "bg-blue-100 text-blue-800"
      case "familiar":
        return "bg-orange-100 text-orange-800"
      case "trusted":
        return "bg-green-100 text-green-800"
    }
  }

  const getStatusIcon = (status: Contact["status"]) => {
    switch (status) {
      case "new":
        return <MessageCircle className="h-3 w-3" />
      case "familiar":
        return <Clock className="h-3 w-3" />
      case "trusted":
        return <Heart className="h-3 w-3" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-md mx-auto space-y-4">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">Contacts</h1>
          <p className="text-gray-600 text-sm">Manage your WhatsApp conversations</p>
        </div>

        <div className="space-y-3">
          {mockContacts.map((contact) => (
            <Card
              key={contact.id}
              className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                selectedContact === contact.id ? "ring-2 ring-orange-500" : ""
              }`}
              onClick={() => setSelectedContact(contact.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <img
                      src={contact.avatar || "/placeholder.svg"}
                      alt={contact.name}
                      className="w-12 h-12 rounded-full object-cover"
                    />
                    {contact.unreadCount > 0 && (
                      <div className="absolute -top-1 -right-1 bg-orange-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                        {contact.unreadCount}
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-medium text-gray-900 truncate">{contact.name}</h3>
                      <span className="text-xs text-gray-500">{contact.timestamp}</span>
                    </div>

                    <p className="text-sm text-gray-600 truncate mb-2">{contact.lastMessage}</p>

                    <Badge className={`text-xs ${getStatusColor(contact.status)}`}>
                      {getStatusIcon(contact.status)}
                      <span className="ml-1 capitalize">{contact.status}</span>
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
