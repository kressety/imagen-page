from io import BytesIO
from os import environ

import gradio as gr
import requests
from PIL import Image


# 获取后端模型列表
def get_models():
    try:
        response = requests.get("https://imagen-api-asia.mealuet.com/models")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch models: {str(e)}"}


# 处理生成请求
def generate_image(provider, model, task, prompt, input_image=None, custom_model=None):
    url = "https://imagen-api-asia.mealuet.com/generate"
    boundary = "WebAppBoundary"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    # 构建 multipart/form-data 数据
    fields = [
        ("provider", provider),
        ("task", task),
        ("prompt", prompt or "default prompt")
    ]

    # 处理模型选择（包括通配符情况）
    if model == "*" and custom_model:
        fields.append(("model", custom_model))
    else:
        fields.append(("model", model))

    # 如果是图生图，添加图片
    if task == "image_to_image" and input_image is not None:
        image_bytes = BytesIO()
        input_image.save(image_bytes, format="PNG")
        fields.append(("image", ("input.png", image_bytes.getvalue(), "image/png")))

    # 构建 multipart/form-data body
    parts = []  # 改用 parts 列表逐步构建
    for key, value in fields:
        if isinstance(value, tuple):  # 处理文件数据
            filename, file_data, content_type = value
            parts.append(f'--{boundary}')
            parts.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"')
            parts.append(f'Content-Type: {content_type}')
            parts.append('')  # 空行分隔头和内容
            parts.append(file_data)  # bytes 数据直接添加
        else:  # 处理普通字段
            parts.append(f'--{boundary}')
            parts.append(f'Content-Disposition: form-data; name="{key}"')
            parts.append('')
            parts.append(value)

    parts.append(f'--{boundary}--')

    # 将所有部分组合成最终的 bytes 数据
    body = b'\r\n'.join(
        part.encode('utf-8') if isinstance(part, str) else part for part in parts
    )

    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()

        # 假设后端返回的是图片二进制数据
        image = Image.open(BytesIO(response.content))
        return image
    except Exception as e:
        return f"Error: {str(e)}"


# 更新模型选择下拉菜单
def update_model_dropdown(provider):
    models_data = get_models()
    if "error" in models_data:
        return gr.Dropdown(choices=["Error loading models"])

    if provider and provider in models_data:
        models = list(models_data[provider].keys())
        return gr.Dropdown(choices=models, value=models[0] if models else None)
    return gr.Dropdown(choices=[])


# 更新任务类型选择
def update_task_dropdown(provider, model):
    models_data = get_models()
    if "error" in models_data:
        return gr.Dropdown(choices=["Error loading models"])

    if provider and model and provider in models_data and model in models_data[provider]:
        tasks = models_data[provider][model]
        return gr.Dropdown(choices=tasks, value=tasks[0] if tasks else None)
    return gr.Dropdown(choices=[])


# 显示自定义模型输入框
def show_custom_model(provider, model):
    return gr.Textbox(visible=(model == "*"))


# Gradio 界面
with gr.Blocks(title="Imagen Project", head='<link rel="icon" type="image/x-icon" href="favicon.ico">') as demo:
    # 获取模型数据
    models_data = get_models()

    with gr.Row():
        with gr.Column():
            # 输入组件
            provider_dropdown = gr.Dropdown(
                label="Provider",
                choices=list(models_data.keys()) if "error" not in models_data else ["Error"],
                value=list(models_data.keys())[0] if "error" not in models_data else "Error"
            )
            model_dropdown = gr.Dropdown(
                label="Model",
                choices=[]
            )
            custom_model_input = gr.Textbox(
                label="Custom Model Name (if * selected)",
                visible=False,
                placeholder="Enter model name for wildcard provider"
            )
            task_dropdown = gr.Dropdown(
                label="Task",
                choices=[]
            )
            prompt_input = gr.Textbox(
                label="Prompt",
                placeholder="Enter your prompt here"
            )
            image_input = gr.Image(
                label="Input Image (for image-to-image)",
                type="pil",
                visible=False
            )
            submit_btn = gr.Button("Generate")

        with gr.Column():
            # 输出组件
            output_image = gr.Image(label="Generated Image")

    # 动态更新
    provider_dropdown.change(
        fn=update_model_dropdown,
        inputs=[provider_dropdown],
        outputs=[model_dropdown]
    )
    model_dropdown.change(
        fn=update_task_dropdown,
        inputs=[provider_dropdown, model_dropdown],
        outputs=[task_dropdown]
    )
    model_dropdown.change(
        fn=show_custom_model,
        inputs=[provider_dropdown, model_dropdown],
        outputs=[custom_model_input]
    )
    task_dropdown.change(
        fn=lambda x: gr.Image(visible=(x == "image_to_image")),
        inputs=[task_dropdown],
        outputs=[image_input]
    )

    # 提交生成
    submit_btn.click(
        fn=generate_image,
        inputs=[provider_dropdown, model_dropdown, task_dropdown, prompt_input, image_input, custom_model_input],
        outputs=[output_image]
    )

# 启动应用
demo.launch(server_name="0.0.0.0", server_port=int(environ["PORT"]))
