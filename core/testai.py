from openai import OpenAI
import os

def test_connection():
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not set.")
            return

        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input="قل: وعليكم السلام فقط."
        )

        # استخراج النص بشكل آمن
        out = response.output[0].content[0]
        text = getattr(out, "text", out)
        text = getattr(text, "value", str(text))

        print("AI:", text)

    except Exception as e:
        print("❌ ERROR:", e)


if __name__ == "__main__":
    test_connection()
