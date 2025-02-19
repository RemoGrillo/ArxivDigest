from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from datetime import date

import argparse
import yaml
import os
from dotenv import load_dotenv
import openai
from relevancy import generate_relevance_score, process_subject_fields
from download_new_papers import get_papers


# Hackathon quality code. Don't judge too harshly.
# Feel free to submit pull requests to improve the code.

topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ",
}

physics_topics = {
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "General Relativity and Quantum Cosmology": "gr-qc",
    "High Energy Physics - Experiment": "hep-ex",
    "High Energy Physics - Lattice": "hep-lat",
    "High Energy Physics - Phenomenology": "hep-ph",
    "High Energy Physics - Theory": "hep-th",
    "Mathematical Physics": "math-ph",
    "Nonlinear Sciences": "nlin",
    "Nuclear Experiment": "nucl-ex",
    "Nuclear Theory": "nucl-th",
    "Physics": "physics",
    "Quantum Physics": "quant-ph",
}


# TODO: surely theres a better way
category_map = {
    "Astrophysics": [
        "Astrophysics of Galaxies",
        "Cosmology and Nongalactic Astrophysics",
        "Earth and Planetary Astrophysics",
        "High Energy Astrophysical Phenomena",
        "Instrumentation and Methods for Astrophysics",
        "Solar and Stellar Astrophysics",
    ],
    "Condensed Matter": [
        "Disordered Systems and Neural Networks",
        "Materials Science",
        "Mesoscale and Nanoscale Physics",
        "Other Condensed Matter",
        "Quantum Gases",
        "Soft Condensed Matter",
        "Statistical Mechanics",
        "Strongly Correlated Electrons",
        "Superconductivity",
    ],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": [
        "Adaptation and Self-Organizing Systems",
        "Cellular Automata and Lattice Gases",
        "Chaotic Dynamics",
        "Exactly Solvable and Integrable Systems",
        "Pattern Formation and Solitons",
    ],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": [
        "Accelerator Physics",
        "Applied Physics",
        "Atmospheric and Oceanic Physics",
        "Atomic and Molecular Clusters",
        "Atomic Physics",
        "Biological Physics",
        "Chemical Physics",
        "Classical Physics",
        "Computational Physics",
        "Data Analysis, Statistics and Probability",
        "Fluid Dynamics",
        "General Physics",
        "Geophysics",
        "History and Philosophy of Physics",
        "Instrumentation and Detectors",
        "Medical Physics",
        "Optics",
        "Physics and Society",
        "Physics Education",
        "Plasma Physics",
        "Popular Physics",
        "Space Physics",
    ],
    "Quantum Physics": ["None"],
    "Mathematics": [
        "Algebraic Geometry",
        "Algebraic Topology",
        "Analysis of PDEs",
        "Category Theory",
        "Classical Analysis and ODEs",
        "Combinatorics",
        "Commutative Algebra",
        "Complex Variables",
        "Differential Geometry",
        "Dynamical Systems",
        "Functional Analysis",
        "General Mathematics",
        "General Topology",
        "Geometric Topology",
        "Group Theory",
        "History and Overview",
        "Information Theory",
        "K-Theory and Homology",
        "Logic",
        "Mathematical Physics",
        "Metric Geometry",
        "Number Theory",
        "Numerical Analysis",
        "Operator Algebras",
        "Optimization and Control",
        "Probability",
        "Quantum Algebra",
        "Representation Theory",
        "Rings and Algebras",
        "Spectral Theory",
        "Statistics Theory",
        "Symplectic Geometry",
    ],
    "Computer Science": [
        "Artificial Intelligence",
        "Computation and Language",
        "Computational Complexity",
        "Computational Engineering, Finance, and Science",
        "Computational Geometry",
        "Computer Science and Game Theory",
        "Computer Vision and Pattern Recognition",
        "Computers and Society",
        "Cryptography and Security",
        "Data Structures and Algorithms",
        "Databases",
        "Digital Libraries",
        "Discrete Mathematics",
        "Distributed, Parallel, and Cluster Computing",
        "Emerging Technologies",
        "Formal Languages and Automata Theory",
        "General Literature",
        "Graphics",
        "Hardware Architecture",
        "Human-Computer Interaction",
        "Information Retrieval",
        "Information Theory",
        "Logic in Computer Science",
        "Machine Learning",
        "Mathematical Software",
        "Multiagent Systems",
        "Multimedia",
        "Networking and Internet Architecture",
        "Neural and Evolutionary Computing",
        "Numerical Analysis",
        "Operating Systems",
        "Other Computer Science",
        "Performance",
        "Programming Languages",
        "Robotics",
        "Social and Information Networks",
        "Software Engineering",
        "Sound",
        "Symbolic Computation",
        "Systems and Control",
    ],
    "Quantitative Biology": [
        "Biomolecules",
        "Cell Behavior",
        "Genomics",
        "Molecular Networks",
        "Neurons and Cognition",
        "Other Quantitative Biology",
        "Populations and Evolution",
        "Quantitative Methods",
        "Subcellular Processes",
        "Tissues and Organs",
    ],
    "Quantitative Finance": [
        "Computational Finance",
        "Economics",
        "General Finance",
        "Mathematical Finance",
        "Portfolio Management",
        "Pricing of Securities",
        "Risk Management",
        "Statistical Finance",
        "Trading and Market Microstructure",
    ],
    "Statistics": [
        "Applications",
        "Computation",
        "Machine Learning",
        "Methodology",
        "Other Statistics",
        "Statistics Theory",
    ],
    "Electrical Engineering and Systems Science": [
        "Audio and Speech Processing",
        "Image and Video Processing",
        "Signal Processing",
        "Systems and Control",
    ],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"],
}


def generate_body(topic, categories, interest, threshold):
    print(f'Generating body with topic {topic} and categories {categories} and interest {interest}, threshold: {threshold}')
    
    # Validate topic
    if topic == "Physics":
        raise RuntimeError("You must choose a physics subtopic.")
    elif topic in physics_topics:
        abbr = physics_topics[topic]
    elif topic in topics:
        abbr = topics[topic]
    else:
        raise RuntimeError(f"Invalid topic {topic}")
    
    # Validate categories
    if categories:
        for category in categories:
            if category not in category_map[topic]:
                raise RuntimeError(f"{category} is not a category of {topic}")
        papers = get_papers(abbr)
        papers = [
            t
            for t in papers
            if bool(set(process_subject_fields(t["subjects"])) & set(categories))
        ]
    else:
        papers = get_papers(abbr)
    
    # If there's an interest, generate relevancy scores
    if interest:
        print(f"Papers: {papers}")
        print(f"Interest: {interest}")
        relevancy, hallucination = generate_relevance_score(
            papers,
            query={"interest": interest},
            threshold_score=threshold,
            num_paper_in_prompt=16,
        )
        
        # Build the HTML body for relevant papers
        body_content = [
            f"""
            <div style="margin-bottom: 1em;">
                <span style="color: #007BFF; font-weight: bold;">Title:</span>
                <a style="color: #007BFF; text-decoration: none;" href="{paper['main_page']}">
                    {paper['title']}
                </a><br>
                
                <span style="color: #28A745; font-weight: bold;">Authors:</span>
                {paper['authors']}<br>
                
                <span style="color: #FFC107; font-weight: bold;">Score:</span>
                {paper['Relevancy score']}<br>
                
                <span style="color: #17A2B8; font-weight: bold;">Reason:</span>
                {paper['Reasons for match']}
            </div>
            """
            for paper in relevancy
        ]
        
        # If there are hallucinations, prepend a warning
        if hallucination:
            warning_message = """
            <div style="color: red; font-weight: bold; margin-bottom: 1em;">
                Warning: the model hallucinated some papers. We have tried to remove them, 
                but the scores may not be accurate.
            </div>
            """
            body = (
                f"<div style='font-family: Arial; color: #333; line-height: 1.5;'>"
                f"{warning_message}"
                f"{'<br>'.join(body_content)}</div>"
            )
        else:
            body = (
                f"<div style='font-family: Arial; color: #333; line-height: 1.5;'>"
                f"{'<br>'.join(body_content)}</div>"
            )

    else:
        # Build the HTML body without interest (no score or reason)
        body_content = [
            f"""
            <div style="margin-bottom: 1em;">
                <span style="color: #007BFF; font-weight: bold;">Title:</span>
                <a style="color: #007BFF; text-decoration: none;" href="{paper['main_page']}">
                    {paper['title']}
                </a><br>
                
                <span style="color: #28A745; font-weight: bold;">Authors:</span>
                {paper['authors']}
            </div>
            """
            for paper in papers
        ]
        body = (
            f"<div style='font-family: Arial; color: #333; line-height: 1.5;'>"
            f"{'<br>'.join(body_content)}</div>"
        )
    
    return body


if __name__ == "__main__":
    # Load the .env file.
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", help="yaml config file to use", default="config.yaml"
    )
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("No openai api key found")
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    topic = config["topic"]
    categories = config["categories"]
    from_email = os.environ.get("FROM_EMAIL")
    to_email = os.environ.get("TO_EMAIL")
    threshold = config["threshold"]
    interest = config["interest"]
    body = generate_body(topic, categories, interest, threshold)
    with open("digest.html", "w") as f:
        print("Writing body:")
        print(body)
        f.write(body)
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("Error: SENDGRID_API_KEY is not set in the environment variables.")
        # Raise an exception so GitHub Actions can fail
        raise RuntimeError("Missing SendGrid API Key.")

    print("Using from email:", from_email)
    
    try:
        # Create the Mail object
        subject = date.today().strftime("Personalized arXiv Digest, %d %b %Y")
        message = Mail(
            from_email=from_email,  # Must be verified in SendGrid
            to_emails=to_email,
            subject=subject,
            html_content=body
        )

        # Send the email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        # Check the response status
        if 200 <= response.status_code < 300:
            print("Send test email: Success!")
        else:
            # Log and raise an error with status code and body
            error_msg = (
                f"Send test email: Failure ({response.status_code})\n"
                f"Response body: {response.body}"
            )
            print(error_msg)
            # Raising this error will make the step fail in GitHub Actions
            raise RuntimeError(error_msg)

        # Print additional response info (useful for debugging)
        print(f"Response Headers: {response.headers}")

    except Exception as e:
        # Log the exception
        print(f"An error occurred while sending email: {str(e)}")
        # Raise the exception to fail the GitHub Actions job
        raise
