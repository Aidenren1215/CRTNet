
import base64
import collections
import time
import io
import json
import requests
from PIL import Image
import cv2
import numpy as np
import glob
import atexit
from sys import platform
import sys
import pdb
from . import communication

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class UnityCommunication(object):

    def __init__(self, url='127.0.0.1', port='8080', file_name=None, x_display=None, no_graphics=False, logging=True,
                 timeout_wait=30, docker_enabled=False):
        self._address = 'http://' + url + ':' + port
        self.port = port
        self.graphics = no_graphics
        self.x_display = x_display
        self.launcher = None
        self.timeout_wait = timeout_wait
        if file_name is not None:
            self.launcher = communication.UnityLauncher(port=port, file_name=file_name, x_display=x_display,
                                                        no_graphics=no_graphics, logging=logging,
                                                        docker_enabled=docker_enabled)
            
            if self.launcher.batchmode:
                print('Getting connection...')
                succeeded = False
                tries = 0
                while tries < 5 and not succeeded:
                    tries += 1
                    try:
                        self.check_connection()
                        succeeded = True
                    except:
                        time.sleep(2)
                if not succeeded:
                    sys.exit()
    def requests_retry_session(
                            self,
                            retries=5,
                            backoff_factor=2,
                            status_forcelist=(500, 502, 504),
                            session=None,
                        ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
    
        return session

    def close(self):
        if self.launcher is not None:
            self.launcher.close()


    def post_command(self, request_dict, repeat=False):
        try:
            if repeat:
                resp = self.requests_retry_session().post(self._address, json=request_dict) 
            else:
                resp = requests.post(self._address, json=request_dict, timeout=self.timeout_wait)
            if resp.status_code != requests.codes.ok:
                raise UnityEngineException(resp.status_code, resp.json())
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise UnityCommunicationException(str(e))

    def check_connection(self):
        response = self.post_command(
                {'id': str(time.time()), 'action': 'idle'}, repeat=True)
        return response['success']
    
    def get_visible_objects(self, camera_index):

        response = self.post_command({'id': str(time.time()), 'action': 'observation', 'intParams': [camera_index]})

        try:
            msg = json.loads(response['message'])
        except Exception as e:
            msg = response['message']

        return response['success'], msg

    def add_character(self, character_resource='Chars/Male1', position=None, initial_room=""):
        mode = 'random'
        pos = [0, 0, 0]
        if position is not None:
            mode = 'fix_position'
            pos = position
        elif not len(initial_room) == 0:
            assert initial_room in ["kitchen", "bedroom", "livingroom", "bathroom"]
            mode = 'fix_room'

        response = self.post_command(
            {'id': str(time.time()), 'action': 'add_character', 
             'stringParams':[json.dumps({
                'character_resource': character_resource,
                'mode': mode,
                'character_position': {'x': pos[0], 'y': pos[1], 'z': pos[2]},
                'initial_room': initial_room
                })]})
        return response['success']

    def move_character(self, char_index, pos):
        response = self.post_command(
            {'id': str(time.time()),
             'action': 'move_character',
             'stringParams':[json.dumps({
                'char_index': char_index,
                'character_position': {'x': pos[0], 'y': pos[1], 'z': pos[2]},
                })]
            })
        return response['success']


    def check(self, script_lines):
        """
        Returns pair (success, message); message is Null when success == True
        """
        response = self.post_command({'id': str(time.time()), 'action': 'check_script', 'stringParams': script_lines})
        return response['success'], response['message']

    def add_camera(self, position=[0,1,0], rotation=[0,0,0]):
        cam_dict = {
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]}
        }
        response = self.post_command(
                {'id': str(time.time()), 'action': 'add_camera',
                    'stringParams': [json.dumps(cam_dict)]})
        return response['success'], response['message']
    
    ################ Mengmi: add new function; modifying existing object transform
    def modify_MMobjectTransform(self, nodeid, position=[0,0.5,0], rotation=[20, 120, 0], scaling=[1, 1, 1]):
        obj_dict = {
                'nodeid': nodeid,
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
                'scaling': {'x': scaling[0], 'y': scaling[1], 'z': scaling[2]}
        }
        response = self.post_command(
                {'id': str(time.time()), 'action': 'modify_MMobjectTransform',
                    'stringParams': [json.dumps(obj_dict)]})
        
        #print('I am sending msg.')
        return response['success'], response['message']
    
    def lookat_MMobjectTransform(self, nodeid, position=[0,0.5,0], rotation=[0, 0, 0], scaling=[1, 1, 1]):
        obj_dict = {
                'nodeid': nodeid,
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
                'scaling': {'x': scaling[0], 'y': scaling[1], 'z': scaling[2]}
        }
        response = self.post_command(
                {'id': str(time.time()), 'action': 'lookat_MMobjectTransform',
                    'stringParams': [json.dumps(obj_dict)]})
        
        #print('I am sending msg.')
        return response['success'], response['message']
    
    def changeMaterial_MMobjectTransform(self, nodeid, materialid, position=[0,0.5,0], rotation=[0, 0, 0], scaling=[1, 1, 1]):
        obj_dict = {
                'nodeid': nodeid,
                'materialid': materialid,
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
                'scaling': {'x': scaling[0], 'y': scaling[1], 'z': scaling[2]}
        }
        response = self.post_command(
                {'id': str(time.time()), 'action': 'changeMaterial_MMobjectTransform',
                    'stringParams': [json.dumps(obj_dict)]})
        
        #print('I am sending msg.')
        return response['success'], response['message']

    def reset_MMobjectTransform(self):
        response = self.post_command(
                {'id': str(time.time()), 'action': 'reset_MMobjectTransform',
                    'intParams': []})
        
        #print('I am sending reset msg.')
        return response['success'], response['message']

    def reset(self, scene_index=None):
        """
        Reset scene
        """
        response = self.post_command({'id': str(time.time()), 'action': 'reset',
                                      'intParams': [] if scene_index is None else [scene_index]})
        return response['success']
    
    def setBathroomTexture(self, scene_index=None):
        """
        Reset scene
        """
        
        if scene_index == 0 or scene_index == 6 or scene_index == 5:
            response = self.post_command({'id': str(time.time()), 'action': 'setBathroomTexture',
                                          'intParams': [] if scene_index is None else [scene_index]})
            return response['success']
        else:
            return True

    def fast_reset(self):
        """
        Reset scene
        """
        response = self.post_command({'id': str(time.time()), 'action': 'fast_reset',
                                      'intParams': []})
        return response['success']

    def camera_count(self):
        """
        Returns the number of cameras in the scene
        """
        #print('camera_count function')
        response = self.post_command({'id': str(time.time()), 'action': 'camera_count'})
        return response['success'], response['value']
    
    def delete_new_camera(self):
        """
        delete new camera added
        """
        #print('camera_count function')
        response = self.post_command({'id': str(time.time()), 'action': 'MMdeleteCamera'})
        return response['success'], response['message']
    
    def getObjInstanceColor(self):
        """
        Returns the number of cameras in the scene
        """
        #print('camera_count function')
        response = self.post_command({'id': str(time.time()), 'action': 'instance_colors'})
        return response['success'], json.loads(response['message'])

    def getObjInstanceColorAndPrefab(self):
        """
        Returns a dict mapping unique object IDs to a tuple of color values and the prefabname.
        {id: ([1., 1., 1.], prefabname)}
        """
        response = self.post_command({'id': str(time.time()), 'action': 'instance_colors_and_prefab'})
        return response['success'], json.loads(response['message'])

    def camera_data(self, camera_indexes):
        """
        Returns camera data for cameras given in camera_indexes list
        """
        if not isinstance(camera_indexes, collections.Iterable):
            camera_indexes = [camera_indexes]
        response = self.post_command({'id': str(time.time()), 'action': 'camera_data',
                                      'intParams': camera_indexes})
        return response['success'], json.loads(response['message'])

    def camera_image(self, camera_indexes, mode='normal', image_width=640, image_height=480):
        """
        Returns a list of renderings of cameras given in camera_indexes.
        Possible modes are: 'normal', 'seg_inst', 'seg_class', 'depth', 'flow'
        """
        if not isinstance(camera_indexes, collections.Iterable):
            camera_indexes = [camera_indexes]

        params = {'mode': mode, 'image_width': image_width, 'image_height': image_height}
        response = self.post_command({'id': str(time.time()), 'action': 'camera_image',
                                      'intParams': camera_indexes, 'stringParams': [json.dumps(params)]})
        return response['success'], _decode_image_list(response['message_list'])

    def instance_colors(self):
        response = self.post_command({'id': str(time.time()), 'action': 'instance_colors'})
        return response['success'], json.loads(response['message'])

    def environment_graph(self):
        """
        Returns environment graph
        """
        response = self.post_command({'id': str(time.time()), 'action': 'environment_graph'})
        return response['success'], json.loads(response['message'])

    def expand_scene(self, new_graph, randomize=False, random_seed=-1, animate_character=False,
                     ignore_placing_obstacles=False, prefabs_map=None, transfer_transform=True):
        """
        Expands scene with the given graph.
        To use randomization set randomize to True.
        To set random seed set random_seed to a non-negative value >= 0,
        random_seed < 0 means that seed is not set
        transfer_transform: whether we want the transforms to appear or not
        """
        config = {'randomize': randomize, 'random_seed': random_seed, 'animate_character': animate_character,
                  'ignore_obstacles': ignore_placing_obstacles, 'transfer_transform': transfer_transform}
        string_params = [json.dumps(config), json.dumps(new_graph)]
        int_params = [int(randomize), random_seed]
        if prefabs_map is not None:
            string_params.append(json.dumps(prefabs_map))
        response = self.post_command({'id': str(time.time()), 'action': 'expand_scene',
                                      'stringParams': string_params})
        try:
            message = json.loads(response['message'])
        except ValueError:
            message = response['message']
        return response['success'], message

    def point_cloud(self):
        response = self.post_command({'id': str(time.time()), 'action': 'point_cloud'})
        return response['success'], json.loads(response['message'])

    def render_script(self, script, randomize_execution=False, random_seed=-1, processing_time_limit=10,
                      skip_execution=False, find_solution=False, output_folder='Output/', file_name_prefix="script",
                      frame_rate=5, image_synthesis=['normal'], save_pose_data=False,
                      image_width=640, image_height=480, gen_vid=True, recording=False,
                      save_scene_states=False, camera_mode=['AUTO'], time_scale=1.0, skip_animation=False):
        """
        :param script: a list of script lines
        :param randomize_execution: randomly choose elements
        :param random_seed: random seed to use when randomizing execution, -1 means that the seed is not set
        :param find_solution: find solution (True) or use graph ids to determine object instances (False)
        :param processing_time_limit: time limit for finding a solution
        :param skip_execution: skip rendering, only check if a solution exists
        :param output_folder: folder to output renderings
        :param file_name_prefix: prefix of created files
        :param frame_rate: frame rate
        :param capture_screenshot: save screenshots
        :param image_synthesis: save depth, segmentation, flow images
        :param save_pose_data: save pose data
        :param save_scene_states: save scene states
        :param character_resource: path to character resource to be used
        :param camera_mode: automatic (AUTO), first person (FIRST_PERSON), top (PERSON_TOP),
        :param image_width: image_height
        :param image_height: image_width
            front person view (PERSON_FRONT)
        :return: pair success (bool), message: (str)
        """
        params = {'randomize_execution': randomize_execution, 'random_seed': random_seed,
                  'processing_time_limit': processing_time_limit, 'skip_execution': skip_execution,
                  'output_folder': output_folder, 'file_name_prefix': file_name_prefix,
                  'frame_rate': frame_rate, 'image_synthesis': image_synthesis, 
                  'find_solution': find_solution,
                  'save_pose_data': save_pose_data, 'save_scene_states': save_scene_states,
                  'camera_mode': camera_mode, 'recording': recording,
                  'image_width': image_width, 'image_height': image_height,
                  'time_scale': time_scale, 'skip_animation': skip_animation}
        response = self.post_command({'id': str(time.time()), 'action': 'render_script',
                                      'stringParams': [json.dumps(params)] + script})
        if response['success']:
            if gen_vid and len(image_synthesis) > 0:
                generate_video(image_synthesis, output_folder, file_name_prefix, frame_rate)
        return response['success'], response['message']

def generate_video(image_syn, output_folder, prefix, frame_rate):
    import os
    import subprocess
    
    curr_folder = os.path.dirname(os.path.realpath(__file__))
    vid_folder = '{}/linux_exec/{}{}/0/'.format(curr_folder, output_folder, prefix)
    print(curr_folder)
    print(vid_folder)
    for vid_mod in image_syn:
        subprocess.call(['ffmpeg', '-i',
                         '{}/Action_%04d_0_{}.png'.format(vid_folder, vid_mod), 
                         '-framerate', str(frame_rate),
                         '-pix_fmt', 'yuv420p',
                         '{}/Action_{}.mp4'.format(vid_folder, vid_mod)])
        # files_delete = glob.glob('{}/Action_*_{}.png'.format(vid_folder, vid_mod))
        # for ft in files_delete: os.remove(ft)
        
def _decode_image(img_string):
    img_bytes = base64.b64decode(img_string)
    if 'PNG' == img_bytes[1:4]:
        img_file = cv2.imdecode(np.fromstring(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    else:
        img_file = cv2.imdecode(np.fromstring(img_bytes, np.uint8), cv2.IMREAD_ANYDEPTH+cv2.IMREAD_ANYCOLOR)
    return img_file


def _decode_image_list(img_string_list):
    image_list = []
    for img_string in img_string_list:
        image_list.append(_decode_image(img_string))
    return image_list


class UnityEngineException(Exception):
    """
    This exception is raised when an error in communication occurs:
    - Unity has received invalid request
    More information is in the message.
    """
    def __init__(self, status_code, resp_dict):
        resp_msg = resp_dict['message'] if 'message' in resp_dict else 'Message not available'
        self.message = 'Unity returned response with status: {0} ({1}), message: {2}'.format(
            status_code, requests.status_codes._codes[status_code][0], resp_msg)


class UnityCommunicationException(Exception):
    def __init__(self, message):
        self.message = message
