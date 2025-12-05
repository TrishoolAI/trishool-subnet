import os
import json
import logging
import tempfile
import traceback
import shutil
import tarfile
import io

import docker
from docker.models.containers import Container
from docker.models.images import Image
from docker import DockerClient

from .sandbox import SandBox
from .constants import (
    PETRI_SANDBOX_IMAGE,
    SANDBOX_MOUNT_PATH,
    CONFIG_FILE_NAME,
    RUN_SCRIPT_NAME,
    RUN_SCRIPT_COMMAND,
    CONFIG_FILE_PATH,
    OUTPUT_FILE_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RUN_ID,
    PYTHONUNBUFFERED,
)

from alignet.utils.logging import get_logger
logger = get_logger()


class SandboxManager:
    docker: DockerClient = None
    sandboxes: dict[str, SandBox] = {}

    def __init__(
        self,
        docker_url: str = "unix://var/run/docker.sock",
    ):
        """Initialize SandboxManager."""
        self.docker = DockerClient(base_url=docker_url)
        self.sandboxes = {}
        logger.info("[SANDBOX] SandboxManager initialized")


    def __del__(self):
        if self.docker:
            self.docker.close()
        self.cleanup_all()

    def kill(self, sandbox_id: str):
        """Kill a sandbox container."""
        sandbox = self.sandboxes.get(sandbox_id)
        if not sandbox:
            logger.warning(f"[SANDBOX] Sandbox <{sandbox_id}> not found")
            return
        container = sandbox.container
        if container:
            try:
                container.kill()
                logger.debug(f"[SANDBOX] Killed sandbox <{sandbox_id}>")
            except Exception as e:
                logger.warning(f"[SANDBOX] Could not kill sandbox <{sandbox_id}>: {e}")

    def build_image(
        self,
        *,
        path: str,
        tag: str,
        dockerfile: str = "Dockerfile",
        arguments: dict = None,
        show_logs: bool = False,
    ) -> Image:
        """Build a Docker image from a specified path with a given tag."""
        try:
            logger.info(f"[SANDBOX] Building image from {path} with tag {tag}")
            image, logs = self.docker.images.build(
                path=path,
                tag=tag,
                rm=True,
                dockerfile=dockerfile,
                buildargs=arguments or {},
            )
            self.docker.images.prune()
            if show_logs:
                for log in logs:
                    if "stream" in log:
                        logger.info(log["stream"].strip())
            return image
        except Exception as e:
            logger.error(f"[SANDBOX] Error building image: {e}")
            return None

    def __finish_with_error(self, sandbox_id, error_msg, result):
        logger.warning(f"[SANDBOX] <{sandbox_id}> failed: {error_msg}")
        result["status"] = "error"
        result["error"] = error_msg
        try:
            sandbox = self.sandboxes.get(sandbox_id)
            sandbox.on_finish(result)
        except Exception as e:
            logger.warning(
                f"[SANDBOX] on_finish() callback failed for <{sandbox_id}>: {e}"
            )
        finally:
            self.cleanup_sandbox(sandbox_id)

    def create_sandbox(
        self,
        *,
        petri_config: dict,
        env_vars: dict,
        on_finish,
        timeout=None,
    ):
        """
        Create a sandbox for running Petri agent with PetriConfig.
        
        This method:
        1. Builds Petri sandbox Docker image if not exists
        2. Creates config.json file with PetriConfig
        3. The container will use run.sh script (already in the image) to execute Petri
        
        Args:
            petri_config: PetriConfig dictionary containing run_id, seed, models, auditor, judge, etc.
            env_vars: Environment variables for the sandbox
            on_finish: Callback function when sandbox finishes
            timeout: Timeout for sandbox execution
            
        Returns:
            sandbox_id: Unique identifier for the created sandbox
        """
        temp_dir = tempfile.mkdtemp()
        sandbox_id = f"sandbox_{os.path.basename(temp_dir)}"
        logger.debug(
            f"[SANDBOX] Created sandbox temp directory for <{sandbox_id}>: {temp_dir}"
        )

        ## save petri config to debug
        # os.makedirs("saved_petri_config", exist_ok=True)
        # with open(f"saved_petri_config/{petri_config['run_id']}.json", "w+") as f:
        #     json.dump(petri_config, f, indent=2)

        try:
            # Write config.json file (will be mounted into container)
            # Petri expects JSON config file with all necessary fields
            config_path = os.path.join(temp_dir, CONFIG_FILE_NAME)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(petri_config, f, indent=2, ensure_ascii=False)

            # Copy run.sh script to temp_dir
            run_script_source = os.path.join(os.path.dirname(__file__), "petri", RUN_SCRIPT_NAME)
            run_script_dest = os.path.join(temp_dir, RUN_SCRIPT_NAME)
            shutil.copy(run_script_source, run_script_dest)
            
            logger.debug(f"[SANDBOX] Wrote Petri config for <{sandbox_id}>: {config_path}")
            logger.debug(f"[SANDBOX] Config: run_id={petri_config.get('run_id')}, models={len(petri_config.get('models', []))}")

            sandbox = SandBox(
                image=PETRI_SANDBOX_IMAGE,
                temp_dir=temp_dir,
                env_vars=env_vars,
                on_finish=on_finish,
                timeout=timeout,
            )

            self.sandboxes[sandbox_id] = sandbox
            return sandbox_id
            
        except Exception as e:
            logger.error(f"[SANDBOX] Failed to create sandbox <{sandbox_id}>: {e}")
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            raise
    
    def _build_petri_image(self):
        """Build Petri sandbox Docker image if it doesn't exist."""
        try:
            # # Check if image already exists
            # try:
            #     self.docker.images.get("petri_sandbox:latest")
            #     logger.debug("[SANDBOX] Petri sandbox image already exists")
            #     return
            # except docker.errors.ImageNotFound:
            #     pass
            
            # Get the absolute path to the petri directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            petri_path = os.path.join(current_dir, "petri")
            
            if not os.path.exists(petri_path):
                logger.error(f"[SANDBOX] Petri Dockerfile not found at {petri_path}")
                raise FileNotFoundError(f"Petri Dockerfile not found at {petri_path}")
            
            logger.info("[SANDBOX] Building Petri sandbox image...")
            self.build_image(
                path=petri_path,
                tag=PETRI_SANDBOX_IMAGE,
                show_logs=True,
            )
            logger.info("[SANDBOX] Petri sandbox image built successfully")
            
        except Exception as e:
            logger.error(f"[SANDBOX] Failed to build Petri image: {e}")
            raise
    

    def _read_file_from_container(self, container: Container, file_path: str) -> bytes:
        """
        Read a file from container using Docker API.
        
        Args:
            container: Docker container object
            file_path: Path to file inside container
            
        Returns:
            File contents as bytes
            
        Raises:
            Exception: If file cannot be read
        """
        bits, stat = container.get_archive(file_path)
        file_obj = io.BytesIO()
        for chunk in bits:
            file_obj.write(chunk)
        file_obj.seek(0)
        tar = tarfile.open(fileobj=file_obj)
        
        # Extract filename from path
        filename = os.path.basename(file_path)
        file_member = tar.extractfile(filename)
        if not file_member:
            # Try with full path
            file_member = tar.extractfile(file_path.lstrip('/'))
        
        if not file_member:
            raise FileNotFoundError(f"File {file_path} not found in container archive")
        
        return file_member.read()
    
    def _read_config_from_container(self, container: Container) -> dict:
        """
        Read config.json from container and extract run_id and output_dir.
        
        Args:
            container: Docker container object
            
        Returns:
            Dictionary with run_id and output_dir, or defaults if not found
        """
        try:
            config_content = self._read_file_from_container(container, CONFIG_FILE_PATH)
            config_dict = json.loads(config_content.decode('utf-8'))
            return {
                "run_id": config_dict.get("run_id", DEFAULT_RUN_ID),
                "output_dir": config_dict.get("output_dir", DEFAULT_OUTPUT_DIR),
            }
        except Exception as e:
            logger.warning(f"[SANDBOX] Could not read {CONFIG_FILE_NAME}: {e}")
            return {
                "run_id": DEFAULT_RUN_ID,
                "output_dir": DEFAULT_OUTPUT_DIR,
            }
    
    def _load_output_json_from_container(self, container: Container, sandbox_id: str, run_id: str, output_dir: str) -> dict:
        """
        Load Petri output JSON from container.
        Tries multiple paths: /sandbox/outputs/output.json first, then fallback to outputs/output.json
        
        Args:
            container: Docker container object
            sandbox_id: Sandbox identifier for logging
            run_id: Run ID from config
            output_dir: Output directory from config
            
        Returns:
            Parsed JSON output as dictionary, or None if not found
        """
        # Try to read /sandbox/outputs/output.json first (created by run.sh)
        try:
            output_content = self._read_file_from_container(container, OUTPUT_FILE_PATH)
            output_json = json.loads(output_content.decode('utf-8'))
            run_id_from_output = output_json.get("run_id", run_id)
            logger.info(
                f"[SANDBOX] <{sandbox_id}> loaded Petri output JSON from {OUTPUT_FILE_PATH} "
                f"(run_id: {run_id_from_output})"
            )
            return output_json
        except Exception as e:
            logger.debug(
                f"[SANDBOX] <{sandbox_id}> Could not read {OUTPUT_FILE_PATH}, trying fallback path: {e}"
            )
            
            # Fallback: try to read from outputs/output.json
            fallback_path = OUTPUT_FILE_PATH
            try:
                output_content = self._read_file_from_container(container, fallback_path)
                output_json = json.loads(output_content.decode('utf-8'))
                run_id_from_output = output_json.get("run_id", run_id)
                logger.info(
                    f"[SANDBOX] <{sandbox_id}> loaded Petri output JSON from {fallback_path} "
                    f"(run_id: {run_id_from_output})"
                )
                return output_json
            except Exception as e2:
                logger.error(f"[SANDBOX] <{sandbox_id}> failed to load Petri output JSON: {e2}")
                return None
    
    def _stream_container_logs(self, container: Container, sandbox_id: str) -> list:
        """
        Stream container logs in real-time and return as list of log lines.
        
        Args:
            container: Docker container object
            sandbox_id: Sandbox identifier for logging
            
        Returns:
            List of log lines
        """
        logger.info(f"[SANDBOX] Streaming logs for <{sandbox_id}>:")
        print(f"\n{'='*60}")
        print(f"SANDBOX LOGS: {sandbox_id}")
        print(f"{'='*60}")
        
        logs_buffer = []
        log_stream = container.logs(stream=True, follow=True, stdout=True, stderr=True)
        
        try:
            for log_chunk in log_stream:
                log_line = log_chunk.decode('utf-8').strip()
                if log_line:
                    logger.info(f"[SANDBOX-{sandbox_id}] {log_line}")
                    logs_buffer.append(log_line)
        except Exception as e:
            logger.warning(f"[SANDBOX] Log streaming interrupted: {e}")
        
        return logs_buffer

    def run_sandbox(self, sandbox_id):
        """
        Run the specified sandbox with Petri agent.
        
        The container will:
        1. Use run.sh script (already in the image) 
        2. Read config.json from mounted volume
        3. Execute Petri with config file and output to /sandbox/outputs/output.json
        """
        sandbox = self.sandboxes.get(sandbox_id)
        if not sandbox:
            logger.warning(f"[SANDBOX] Sandbox <{sandbox_id}> not found for running")
            return
        
        temp_dir = sandbox.temp_dir
        result = {
            "status": "success",
            "output": None,
            "output_json": None,
            "logs": "",
            "error": None,
            "traceback": None,
            "exit_code": 0,
        }

        try:
            # Prepare container arguments
            container_args = {
                "image": sandbox.image,
                "command": RUN_SCRIPT_COMMAND,
                "name": sandbox_id,
                "volumes": {temp_dir: {"bind": SANDBOX_MOUNT_PATH, "mode": "rw"}},
                "environment": {
                    PYTHONUNBUFFERED: PYTHONUNBUFFERED,
                    **sandbox.env_vars,
                },
                "remove": False,
                "detach": True,
            }
            
            # Run the sandbox container
            sandbox.container = self.docker.containers.run(**container_args)
            logger.debug(f"[SANDBOX] Started container for <{sandbox_id}>: {type(sandbox.container)}")

            # Stream logs while container is running
            logs_buffer = self._stream_container_logs(sandbox.container, sandbox_id)

            # Wait for container to finish
            exit_code = sandbox.container.wait()
            exit_code = exit_code["StatusCode"]
            result["exit_code"] = exit_code
            logger.debug(f"[SANDBOX] <{sandbox_id}> finished running with exit code: {exit_code}")
            
            print(f"{'='*60}")
            print(f"SANDBOX COMPLETED: {sandbox_id} (exit code: {exit_code})")
            print(f"{'='*60}\n")

            # Store logs
            result["logs"] = "\n".join(logs_buffer)
            logger.debug(f"[SANDBOX] <{sandbox_id}> captured {len(logs_buffer)} lines of logs")

            # Handle exit code errors
            if exit_code != 0:
                error_msg = f"Container exited with non-zero exit code: {exit_code}"
                logger.error(f"[SANDBOX] <{sandbox_id}> {error_msg}")
                result["error"] = error_msg
                result["status"] = "error"

            else:
                # Read config to get run_id and output_dir
                config_info = self._read_config_from_container(sandbox.container)
                run_id = config_info["run_id"]
                output_dir = config_info["output_dir"]
                
                # Load output JSON
                output_json = self._load_output_json_from_container(
                    sandbox.container, sandbox_id, run_id, output_dir
                )
                
                if output_json:
                    result["output_json"] = output_json
                elif result["status"] != "error":
                    # Only set error if we didn't already have an error
                    result["error"] = "Output JSON not found in container"
                    result["status"] = "error"

            # Remove container
            sandbox.container.remove()
            sandbox.container = None

        except Exception as e:
            # An error occurred while running the sandbox
            self.__finish_with_error(sandbox_id, str(e), result)
            result["traceback"] = traceback.format_exc()
            return
            
        try:
            sandbox.on_finish(result)
        except Exception as e:
            logger.warning(
                f"[SANDBOX] on_finish() callback failed for <{sandbox_id}>: {e}"
            )
        finally:
            self.cleanup_sandbox(sandbox_id)

    def cleanup_sandbox(self, sandbox_id):
        """Clean up a sandbox and its temporary directory."""
        sandbox_info = self.sandboxes.get(sandbox_id)
        if not sandbox_info:
            logger.warning(f"[SANDBOX] Sandbox <{sandbox_id}> not found for cleanup")
            return

        container = sandbox_info.container

        # Stop and remove container if it exists
        if container:
            try:
                container.stop()
                container.remove()
                logger.debug(
                    f"[SANDBOX] Stopped and removed container for <{sandbox_id}>"
                )
            except Exception as e:
                logger.warning(
                    f"[SANDBOX] Could not clean up container for <{sandbox_id}>: {e}"
                )

        # Clean up temp directory
        del self.sandboxes[sandbox_id]

        logger.debug(f"[SANDBOX] Cleaned up sandbox <{sandbox_id}>")

    def cleanup_all(self):
        """Clean up all sandboxes."""
        sandbox_ids = list(self.sandboxes.keys())
        for sandbox_id in sandbox_ids:
            self.cleanup_sandbox(sandbox_id)
