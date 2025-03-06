"use client"

import { redirect } from 'next/navigation';

export default function Home() {
    // Redirect from the root route to the home page
    redirect('/home');
}