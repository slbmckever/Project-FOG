def inject_background():
    """Inject background video from local assets/bg.mp4 if available; fallback to gradient."""

    if VIDEO_PATH.exists():
        video_bytes = VIDEO_PATH.read_bytes()
        video_b64 = base64.b64encode(video_bytes).decode()

        st.markdown(f"""
        <style>
            #video-bg-container {{
                position: fixed !important;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                z-index: -1;
                overflow: hidden;
                pointer-events: none;
            }}
            #video-bg-container video {{
                position: absolute;
                top: 50%; left: 50%;
                min-width: 100%;
                min-height: 100%;
                transform: translate(-50%, -50%);
                object-fit: cover;
            }}
            #video-bg-container .overlay {{
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: rgba(15, 23, 42, 0.75);
            }}
        </style>

        <div id="video-bg-container">
            <video autoplay muted loop playsinline>
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
            <div class="overlay"></div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # fallback gradient
        st.markdown("""
        <style>
            #gradient-bg {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                z-index: -1;
                background: linear-gradient(
                    -45deg,
                    #0f172a,
                    #1e1b4b,
                    #172554,
                    #0c4a6e,
                    #1e1b4b,
                    #0f172a
                );
                background-size: 400% 400%;
                animation: gradientMove 20s ease infinite;
            }}
            @keyframes gradientMove {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
        </style>
        <div id="gradient-bg"></div>
        """, unsafe_allow_html=True)
