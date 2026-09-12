import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
    return (
        <main className="shell">
            <nav>
                <b>Build a simple student task management app with login, tasks, dashboard and repo</b>
                <span>AutoDev AI</span>
            </nav>

            <section className="hero">
                <p className="badge">
                    AI-generated application
                </p>

                <h1>Build a simple student task management app with login, tasks, dashboard and repo</h1>

                <p>Build a simple student task management app with login, tasks, dashboard and reports.</p>

                <button   
                    type="button"
                    onclick={()=> alert("Application started")}
                >
                    Get Started
                </button>
                
            </section>
        </main>
    );
}

const root = document.getElementById("root");

if (root) {
    createRoot(root).render(<App />);
}
